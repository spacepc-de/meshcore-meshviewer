from django.core.management.base import BaseCommand
from django.utils import timezone

from ...services import _run_contacts_command, _run_contact_info_command


class Command(BaseCommand):
    help = "Fetch contact list and persist per-contact telemetry snapshots via contact_info."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Max contacts to process (0 = all)")
        parser.add_argument("--sleep", type=float, default=0.2, help="Seconds to sleep between contact_info calls")

    def handle(self, *args, **options):
        limit = options.get("limit") or 0
        sleep_s = options.get("sleep") or 0.0

        items = _run_contacts_command()
        names = []
        for it in items:
            n = None
            if isinstance(it, dict):
                n = it.get("name") or it.get("adv_name")
            elif isinstance(it, str):
                n = it
            if n:
                names.append(n)

        if limit > 0:
            names = names[:limit]

        self.stdout.write(self.style.MIGRATE_HEADING(f"Processing {len(names)} contacts @ {timezone.now().isoformat()}"))

        import time as _time

        ok = 0
        for n in names:
            try:
                _run_contact_info_command(n)
                ok += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"contact_info failed for '{n}': {e}"))
            if sleep_s > 0:
                _time.sleep(sleep_s)

        self.stdout.write(self.style.SUCCESS(f"Done. {ok}/{len(names)} contacts persisted."))

