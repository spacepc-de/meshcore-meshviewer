import time
import os
import traceback
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from ...services import (
    _run_contacts_command,
    _run_contact_info_command,
    _run_req_status_command,
    _run_req_telemetry_command,
    get_collector_interval_default,
    get_collector_enable_req_telemetry_default,
    get_collector_enable_req_status_default,
    sync_unread_messages,
)


class Command(BaseCommand):
    help = "Run a background loop to fetch contact_info for all contacts at configured intervals."

    def add_arguments(self, parser):
        parser.add_argument("--min-interval", type=int, default=30, help="Safety: minimum allowed interval seconds")
        parser.add_argument("--debug", action="store_true", help="Print verbose debug output, including raw CLI snippets on errors")

    def handle(self, *args, **options):
        min_interval = max(5, int(options.get("min_interval") or 30))
        debug = bool(options.get("debug"))
        self.stdout.write(self.style.MIGRATE_HEADING("Starting contact collector loop"))
        while True:
            try:
                interval = max(min_interval, int(get_collector_interval_default()))
            except Exception:
                interval = max(min_interval, 300)
            # Messages poll interval (seconds)
            try:
                msg_poll = max(2, int(os.getenv("MESSAGES_POLL_SECONDS", "5")))
            except Exception:
                msg_poll = 5

            started = timezone.now()
            try:
                items = _run_contacts_command()
                if debug:
                    self.stdout.write(self.style.HTTP_INFO(f"contacts: got {len(items)} entries"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"contacts failed: {e}"))
                items = []

            names = []
            for it in items:
                n = None
                if isinstance(it, dict):
                    # Prefer human-readable name, but fall back to public_key (CLI can often resolve by key/prefix)
                    n = it.get("name") or it.get("adv_name") or it.get("display_name") or it.get("label") or it.get("public_key")
                elif isinstance(it, str):
                    n = it
                if n:
                    names.append(str(n))

            # No prompt probing in stateless mode

            ok = 0
            for n in names:
                try:
                    if debug:
                        self.stdout.write(self.style.HTTP_INFO(f"contact_info '{n}'..."))
                    _run_contact_info_command(n)
                    # Enhance with status/telemetry (RSSI/SNR/coords/type/flags/battery)
                    if get_collector_enable_req_status_default():
                        try:
                            st = _run_req_status_command(n)
                            if debug and isinstance(st, dict):
                                batt_mv = None
                                batt_pct = None
                                # Try various keys
                                for k in ("battery_mv", "bat_mv", "vbat_mv"):
                                    v = st.get(k)
                                    try:
                                        if v is not None:
                                            vi = int(float(v))
                                            if vi > 1000:
                                                batt_mv = vi
                                                break
                                    except Exception:
                                        pass
                                for k in ("battery_percent", "battery", "bat_percent", "soc", "charge", "level"):
                                    v = st.get(k)
                                    try:
                                        if v is None:
                                            continue
                                        vf = float(v)
                                        if 0.0 < vf <= 1.0:
                                            batt_pct = vf * 100.0
                                            break
                                        if 0.0 <= vf <= 100.0:
                                            batt_pct = vf
                                            break
                                    except Exception:
                                        pass
                                rssi = st.get("rssi")
                                snr = st.get("snr")
                                batt_str = (
                                    (f"{batt_pct:.0f}%" if batt_pct is not None else None) or
                                    (f"{batt_mv} mV" if batt_mv is not None else None) or
                                    "—"
                                )
                                self.stdout.write(self.style.HTTP_INFO(
                                    f"status '{n}': batt={batt_str}"
                                    + (f" rssi={rssi}" if rssi is not None else "")
                                    + (f" snr={snr}" if snr is not None else "")
                                ))
                        except Exception:
                            pass
                    elif debug:
                        self.stdout.write(self.style.HTTP_INFO(f"status disabled in settings; skipping '{n}'"))

                    # Optional: req_telemetry can be disabled via settings
                    if get_collector_enable_req_telemetry_default():
                        try:
                            tl = _run_req_telemetry_command(n)
                            if debug and isinstance(tl, dict):
                                la = tl.get("adv_lat")
                                lo = tl.get("adv_lon")
                                ladv = tl.get("last_advert")
                                pos = None
                                try:
                                    if la is not None and lo is not None:
                                        pos = f"{float(la):.4f},{float(lo):.4f}"
                                except Exception:
                                    pos = None
                                self.stdout.write(self.style.HTTP_INFO(
                                    f"telemetry '{n}': last_advert={ladv if ladv is not None else '—'}"
                                    + (f" pos={pos}" if pos else "")
                                ))
                        except Exception:
                            pass
                    elif debug:
                        self.stdout.write(self.style.HTTP_INFO(f"telemetry disabled in settings; skipping '{n}'"))

                    ok += 1
                except Exception as e:
                    # Keep this concise even in debug; timeouts are expected sometimes
                    self.stderr.write(self.style.ERROR(f"contact_info failed for '{n}': {e}"))

            self.stdout.write(self.style.SUCCESS(f"Cycle done: {ok}/{len(names)} contacts at {started.isoformat()}"))

            # Within the configured interval, poll unread messages frequently
            deadline = started + timezone.timedelta(seconds=interval)
            while timezone.now() < deadline:
                try:
                    added = sync_unread_messages()
                    if debug:
                        self.stdout.write(self.style.HTTP_INFO(f"messages: +{added}"))
                except Exception as e:
                    if debug:
                        self.stderr.write(self.style.WARNING(f"messages poll failed: {e}"))
                time.sleep(msg_poll)

            # Avoid stale DB connections when sleeping long
            try:
                connection.close()
            except Exception:
                pass
            # Next loop will compute a fresh interval again
