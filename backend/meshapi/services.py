import json
import os
import shlex
import subprocess
import shutil
import re
import select
import time
import threading
from datetime import timedelta
from typing import Any, Dict, Tuple, Optional, List

from django.utils import timezone

from .models import (
    NodeInfo,
    Contact,
    ContactTelemetry,
    CollectorConfig,
    Message,
    AutomationRule,
    MQTTConfig,
)


DEFAULT_SAMPLE = {
    "adv_type": 1,
    "tx_power": 22,
    "max_tx_power": 22,
    "public_key": "d398f2f2a5acd301098318fc9d555334aab2bad8806635393a413244194cd28d",
    "adv_lat": 0.0,
    "adv_lon": 0.0,
    "adv_loc_policy": 0,
    "telemetry_mode_env": 0,
    "telemetry_mode_loc": 0,
    "telemetry_mode_base": 0,
    "manual_add_contacts": False,
    "radio_freq": 869.618,
    "radio_bw": 62.5,
    "radio_sf": 8,
    "radio_cr": 8,
    "name": "JOST_DEV",
}

DEFAULT_CONTACTS_SAMPLE: List[Dict[str, Any]] = [
    {
        "name": "Node A",
        "public_key": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "last_seen": "2025-01-01T12:00:00Z",
        "rssi": -70,
    },
    {
        "name": "Node B",
        "public_key": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "last_seen": "2025-01-01T12:05:00Z",
        "rssi": -62,
    },
]

# Lightweight throttling for background refresh tasks to avoid spawning too many workers
_EXTRAS_REFRESH_MIN_INTERVAL_S = 20.0
_BASE_REFRESH_MIN_INTERVAL_S = 10.0
_last_extras_refresh_started: float = 0.0
_last_base_refresh_started: float = 0.0


def _parse_json_output(output: str) -> Any:
    output = output.strip()
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        start = output.find('{')
        end = output.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = output[start:end+1]
            return json.loads(candidate)
        # Also try array
        start = output.find('[')
        end = output.rfind(']')
        if start != -1 and end != -1 and end > start:
            candidate = output[start:end+1]
            return json.loads(candidate)
        raise


def _meshcore_bin() -> str:
    return (os.getenv("MESHCORE_CLI") or "meshcore-cli").strip() or "meshcore-cli"


def _meshcore_target() -> str:
    return (os.getenv("MESHCORE_TARGET") or "").strip()


def _exec_cli_json(command: str, timeout: int = 30) -> Tuple[str, Any]:
    """Execute meshcore-cli once with --json and return (stdout, parsed_data).

    We pass the command as a single string argument to --json, allowing spaces/quotes within.
    """
    meshcore_bin = _meshcore_bin()
    target = _meshcore_target()
    if not target:
        raise RuntimeError("MESHCORE_TARGET not configured")
    args = [meshcore_bin, "-t", target, "-j"] + shlex.split(command)
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"meshcore-cli failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
    stdout = proc.stdout or ""
    data = _parse_json_output(stdout)
    return stdout, data


def _run_self_telemetry() -> Optional[Dict[str, Any]]:
    """Return self telemetry from the local node via one-shot JSON.

    Uses meshcore-cli `self_telemetry` (available over BLE/TCP/Serial). Returns
    a dict on success, or None on error.
    """
    try:
        stdout, data = _exec_cli_json("self_telemetry")
        _extract_and_persist_chats(stdout)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def _run_version_info() -> Optional[Dict[str, Any]]:
    """Return device query info (model, version, build date) via `ver`.

    Returns a dict like {"model": ..., "ver": ..., "fw ver": ..., "fw_build": ...}
    or None if unavailable.
    """
    try:
        stdout, data = _exec_cli_json("ver")
        _extract_and_persist_chats(stdout)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def _exec_shell_json(cmd_tpl: str, timeout: int = 30) -> Tuple[str, Any]:
    """Execute a shell command template that is expected to output JSON.

    Returns (stdout, parsed_data).
    """
    proc = subprocess.run(["/bin/sh", "-lc", cmd_tpl], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
    stdout = proc.stdout or ""
    data = _parse_json_output(stdout)
    return stdout, data


def _extract_and_persist_chats(raw: str) -> None:
    """Parse any inline chat snippets from raw CLI output and persist as incoming messages.

    Handles concatenated messages and prompt echoes gracefully.
    """
    if not raw:
        return
    # Delimiter '(D):' and prompt separator '🭨'
    delim_re = re.compile(r"\(D\):\s*")
    prompt_names = re.findall(r"(?<!\w)([A-Za-z0-9][A-Za-z0-9_-]{0,63})🭨", raw)
    prompt_positions = [m.start() for m in re.finditer("🭨", raw)]

    delims = list(delim_re.finditer(raw))
    if not delims:
        return
    try:
        known_names = list(Contact.objects.exclude(name="").values_list("name", flat=True))
    except Exception:
        known_names = []
    known_names = sorted(set(n for n in known_names if isinstance(n, str)), key=len, reverse=True)

    parts = []
    for i, d in enumerate(delims):
        name_end = d.start()
        while name_end > 0 and raw[name_end - 1].isspace():
            name_end -= 1
        text_start = d.end()
        left_bound = 0
        if i > 0:
            left_bound = max(left_bound, delims[i - 1].end())
        if prompt_positions:
            left_bound = max(left_bound, max([p + 1 for p in prompt_positions if p < name_end], default=0))
        window = raw[left_bound:name_end].rstrip()
        name = None
        for kn in known_names:
            if window.endswith(kn):
                name = kn
                name_start = name_end - len(kn)
                break
        if not name:
            tail = window[-64:]
            m_tail = re.search(r"([A-Za-z0-9 _\-]{1,64})\s*$", tail)
            if m_tail:
                cand = m_tail.group(1).strip()
                if cand:
                    name = cand
                    name_start = name_end - len(cand)
            if not name:
                cand = window[-16:].strip()
                name = cand
                name_start = name_end - len(cand)
        parts.append({"name": name or "", "name_start": name_start, "text_start": text_start})

    for i, part in enumerate(parts):
        name = part["name"].strip()
        if not name:
            continue
        text_start = part["text_start"]
        next_name_start = parts[i + 1]["name_start"] if i + 1 < len(parts) else None
        sep_pos = raw.find("🭨", text_start)
        text_end = len(raw)
        if next_name_start is not None:
            text_end = min(text_end, next_name_start)
        if sep_pos != -1:
            text_end = min(text_end, sep_pos)
        text = raw[text_start:text_end].strip()
        if not text:
            continue
        if prompt_names:
            for pn in prompt_names:
                if pn and text.endswith(pn):
                    text = text[: -len(pn)].rstrip()
                    break
        if not text:
            continue
        # Persist
        contact = Contact.objects.filter(name=name).order_by("-last_seen").first()
        try:
            cutoff = timezone.now() - timedelta(seconds=3)
            if Message.objects.filter(direction="in", name=name, text=text, ts__gte=cutoff).exists():
                continue
        except Exception:
            pass
        try:
            Message.objects.create(
                contact=contact,
                name=name,
                public_key=contact.public_key if contact else None,
                direction="in",
                text=text,
                ts=timezone.now(),
                raw=raw,
            )
        except Exception:
            pass


def _run_info_command(name: str) -> Dict[str, Any]:
    """
    Execute an external command to retrieve node info as JSON.

    Uses env var `MESH_INFO_COMMAND` (or fallback `MESHCORE_INFO_COMMAND`).
    If the command contains `{name}`, it will be formatted with the node name.

    In DEBUG and if not configured, returns DEFAULT_SAMPLE.
    """
    cmd_tpl = (
        os.getenv("MESH_INFO_COMMAND")
        or os.getenv("MESHCORE_INFO_COMMAND")
        or ""
    ).strip()

    if not cmd_tpl:
        # Development fallback
        from django.conf import settings
        if getattr(settings, "DEBUG", False):
            return DEFAULT_SAMPLE
        # Use meshcore-cli one-shot JSON
        stdout, data = _exec_cli_json("infos")
        _extract_and_persist_chats(stdout)
        if isinstance(data, dict):
            return data
        raise RuntimeError("Invalid infos output shape")
    else:
        cmd = cmd_tpl.format(name=name)
        stdout, data = _exec_shell_json(cmd)
        _extract_and_persist_chats(stdout)
        if isinstance(data, dict):
            return data
        raise RuntimeError("Invalid infos output shape")


def _run_contacts_command() -> List[Dict[str, Any]]:
    """
    Execute an external command to retrieve contacts as JSON (list or object).

    Uses env var `MESH_CONTACTS_COMMAND` (or fallback to detected meshcore-cli).
    In DEBUG and if not configured, returns DEFAULT_CONTACTS_SAMPLE.
    """
    cmd_tpl = (
        os.getenv("MESH_CONTACTS_COMMAND")
        or ""
    ).strip()

    if not cmd_tpl:
        # One-shot JSON via meshcore-cli
        try:
            stdout, data = _exec_cli_json("contacts")
        except Exception as e:
            # Fallback to text run (without --json) to try parse plain output
            meshcore_bin = _meshcore_bin()
            target = _meshcore_target()
            if not target:
                raise
            proc = subprocess.run([meshcore_bin, "-t", target, "contacts"], capture_output=True, text=True, timeout=15)
            if proc.returncode != 0:
                raise RuntimeError(f"Contacts command failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
            raw = proc.stdout or ""
            _extract_and_persist_chats(raw)
            # Fall through to plain text parsing below
        else:
            _extract_and_persist_chats(stdout)
            # Normalize various JSON shapes into a list of contact dicts
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                # Common shape from meshcore-cli: mapping of public_key -> contact dict
                # Also support nested keys like { contacts: {...} } or { items: [...] }
                for key in ("contacts", "items", "data"):
                    val = data.get(key)
                    if isinstance(val, list):
                        return val
                    if isinstance(val, dict):
                        try:
                            vals = list(val.values())
                            if vals and all(isinstance(v, dict) for v in vals):
                                return vals
                        except Exception:
                            pass
                # If top-level itself looks like a mapping of contacts, flatten values
                try:
                    vals = list(data.values())
                    if vals and all(isinstance(v, dict) for v in vals):
                        return vals
                except Exception:
                    pass
                # Else treat as a single contact-like object
                return [data]
            raw = stdout
    else:
        proc = subprocess.run(["/bin/sh", "-lc", cmd_tpl], capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Contacts command failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
            )
        raw = proc.stdout or ""
        _extract_and_persist_chats(raw)

    # Plain text parsing as fallback: one contact per line, ignore headers and empty lines.
    raw = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", raw)
    lines = [ln.strip() for ln in raw.replace("\r", "").split("\n")]
    items: List[Dict[str, Any]] = []
    for ln in lines:
        if not ln:
            continue
        low = ln.lower()
        # Skip any prompt/echo lines that contain the special separator
        if "🭨" in ln:
            continue
        # Skip banner/log lines
        if low.startswith('info:meshcore:') or low.startswith('warning:') or 'interactive mode' in low or 'will end interactive mode' in low or 'use "to"' in low or 'line starting with' in low:
            continue
        # skip command echo / headers like "contacts"
        if low.strip() == "contacts":
            # If the line is ONLY 'contacts' or clearly a header, skip it.
            continue

        # Extract 64-hex public key if present
        key_match = re.search(r"\b[0-9a-fA-F]{64}\b", ln)
        public_key = key_match.group(0) if key_match else None
        # Remove key from name line for cleaner name
        name_part = ln
        if public_key:
            name_part = name_part.replace(public_key, "").strip()

        # Extract simple metrics if present
        rssi_match = re.search(r"RSSI\s*[:=]\s*(-?\d+)", ln, re.IGNORECASE)
        snr_match = re.search(r"SNR\s*[:=]\s*(-?\d+(?:\.\d+)?)", ln, re.IGNORECASE)

        name = name_part.strip("-:| ")
        if not name and public_key:
            name = public_key
        if not name:
            # nothing meaningful on this line
            continue

        item: Dict[str, Any] = {"name": name}
        if public_key:
            item["public_key"] = public_key
        if rssi_match:
            try:
                item["rssi"] = int(rssi_match.group(1))
            except Exception:
                pass
        if snr_match:
            try:
                item["snr"] = float(snr_match.group(1))
            except Exception:
                pass

        items.append(item)

    if not items:
        # Nothing parsed, return DEBUG sample in debug or raise
        from django.conf import settings
        if getattr(settings, "DEBUG", False):
            return DEFAULT_CONTACTS_SAMPLE
        raise RuntimeError("Could not parse contacts output")

    return items


def _run_contact_info_command(name: str) -> Dict[str, Any]:
    """
    Execute an external command to retrieve details for a single contact.

    Uses env var `MESH_CONTACT_INFO_COMMAND` (format with `{name}`) or falls back
    to an interactive pipeline using meshcore-cli with `contact_info NAME`.
    """
    cmd_tpl = (
        os.getenv("MESH_CONTACT_INFO_COMMAND") or ""
    ).strip()

    if not cmd_tpl:
        # One-shot JSON via meshcore-cli
        from django.conf import settings
        try:
            stdout, data = _exec_cli_json(f'contact_info "{name}"')
            _extract_and_persist_chats(stdout)
            if isinstance(data, dict):
                _persist_contact_info(data)
                return data
            if isinstance(data, list) and data and isinstance(data[0], dict):
                _persist_contact_info(data[0])
                return data[0]
        except Exception:
            if getattr(settings, "DEBUG", False):
                info = {
                    "adv_name": name,
                    "public_key": "0" * 64,
                    "type": 1,
                    "flags": 0,
                    "out_path_len": -1,
                    "out_path": "",
                    "last_advert": int(timezone.now().timestamp()),
                    "adv_lat": 0.0,
                    "adv_lon": 0.0,
                    "lastmod": int(timezone.now().timestamp()),
                }
                _persist_contact_info(info)
                return info
            raise
    else:
        cmd = cmd_tpl.format(name=name)
        stdout, data = _exec_shell_json(cmd)
        _extract_and_persist_chats(stdout)
        info = _ensure_contact_info_json(stdout)
        _persist_contact_info(info)
        return info


def _ensure_contact_info_json(raw: str) -> Dict[str, Any]:
    raw = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", raw)  # strip ANSI
    try:
        data = _parse_json_output(raw)
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        raise RuntimeError("Unexpected contact_info output shape")
    except Exception as e:
        raise RuntimeError(f"Invalid JSON from contact_info: {e}")


def _persist_contact_info(info: Dict[str, Any]) -> None:
    """Persist contact + telemetry snapshot.

    Accepts dicts from various CLI calls. Tries to resolve contact via
    public_key, else via adv_name/name.
    """
    public_key = info.get("public_key")
    adv_name = info.get("adv_name") or info.get("name") or ""

    contact: Optional[Contact] = None
    if isinstance(public_key, str) and public_key:
        contact, _ = Contact.objects.get_or_create(public_key=public_key, defaults={
            "name": adv_name or "",
            "first_seen": timezone.now(),
            "last_seen": timezone.now(),
        })
    elif adv_name:
        try:
            contact = Contact.objects.filter(name=adv_name).order_by("-last_seen").first()
        except Exception:
            contact = None
        if contact is None:
            # Cannot persist without resolving a contact
            return

    # Update latest name/last_seen
    changed = False
    if adv_name and adv_name != (contact.name or ""):
        contact.name = adv_name
        changed = True
    contact.last_seen = timezone.now()
    if changed:
        contact.save()
    else:
        # still update last_seen without touching other fields
        Contact.objects.filter(pk=contact.pk).update(last_seen=contact.last_seen)

    # Battery parsing heuristics (from various CLI payloads)
    def _parse_battery(payload: Dict[str, Any]) -> Tuple[Optional[int], Optional[float]]:
        mv: Optional[int] = None
        pct: Optional[float] = None
        # candidates
        candidates_mv = [
            payload.get("battery_mv"), payload.get("bat_mv"), payload.get("vbat_mv"), payload.get("vbat"), payload.get("vbatt"),
        ]
        candidates_pct = [
            payload.get("battery_percent"), payload.get("battery"), payload.get("bat_percent"), payload.get("soc"), payload.get("charge"),
        ]
        # Some responses use 'level' for battery; interpret by range
        lvl = payload.get("level")
        if lvl is not None:
            try:
                val = float(lvl)
                if val > 1000:
                    mv = int(val)
                elif 0 <= val <= 100:
                    pct = float(val)
                elif 0.0 < val < 1.0:
                    pct = float(val) * 100.0
            except Exception:
                pass
        # Direct candidates
        for v in candidates_mv:
            try:
                if v is None:
                    continue
                vi = int(v)
                if vi > 1000:
                    mv = vi
                    break
            except Exception:
                continue
        for v in candidates_pct:
            try:
                if v is None:
                    continue
                vf = float(v)
                if 0.0 <= vf <= 1.0:
                    pct = vf * 100.0
                    break
                if 0.0 <= vf <= 100.0:
                    pct = vf
                    break
            except Exception:
                continue
        return mv, pct

    bat_mv, bat_pct = _parse_battery(info)

    # Store telemetry snapshot
    ContactTelemetry.objects.create(
        contact=contact,
        adv_name=adv_name or "",
        last_advert=info.get("last_advert"),
        adv_lat=info.get("adv_lat"),
        adv_lon=info.get("adv_lon"),
        rssi=info.get("rssi"),
        snr=info.get("snr"),
        battery_mv=bat_mv,
        battery_percent=bat_pct,
        type=info.get("type"),
        flags=info.get("flags"),
        out_path_len=info.get("out_path_len"),
        out_path=info.get("out_path") or "",
        lastmod=info.get("lastmod"),
        raw=info,
    )

    # Reconcile past messages that arrived before contact was known (no public_key)
    try:
        if adv_name:
            Message.objects.filter(name=adv_name, public_key__isnull=True).update(public_key=public_key, contact=contact)
    except Exception:
        pass


def get_collector_interval_default() -> int:
    try:
        obj = CollectorConfig.objects.order_by('-id').first()
        if obj and isinstance(obj.interval_seconds, int) and obj.interval_seconds >= 0:
            return obj.interval_seconds
    except Exception:
        pass
    return 300


def get_collector_enable_req_telemetry_default() -> bool:
    """Return whether req_telemetry should be performed by the collector.

    Defaults to False if unset or on error.
    """
    try:
        obj = CollectorConfig.objects.order_by('-id').first()
        if obj is not None:
            return bool(getattr(obj, 'enable_req_telemetry', False))
    except Exception:
        pass
    return False


def get_collector_enable_req_status_default() -> bool:
    """Return whether req_status should be performed by the collector.

    Defaults to True if unset or on error (backward-compatible behavior).
    """
    try:
        obj = CollectorConfig.objects.order_by('-id').first()
        if obj is not None:
            # Default True if field missing
            val = getattr(obj, 'enable_req_status', True)
            return bool(val) if val is not None else True
    except Exception:
        pass
    return True


def _run_meshcore_with_pty(meshcore_bin: str, target: str, lines: List[str], timeout_s: float = 5.0) -> str:
    """Run meshcore-cli in a PTY, send lines, capture output until JSON likely complete or timeout.

    We stop early if we can successfully parse a JSON object from the buffer.
    """
    # Start interactive CLI under PTY
    master_fd, slave_fd = os.openpty()
    try:
        proc = subprocess.Popen(
            [meshcore_bin, "-t", target],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)  # parent doesn't use slave

        # Send commands
        for line in lines:
            os.write(master_fd, (line + "\n").encode("utf-8", errors="ignore"))

        buf = b""
        start = time.time()
        last_try = 0.0
        while time.time() - start < timeout_s:
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in r:
                try:
                    chunk = os.read(master_fd, 4096)
                    if not chunk:
                        break
                    buf += chunk
                except OSError:
                    break
            # Try to parse JSON every ~100ms
            now = time.time()
            if now - last_try > 0.1 and buf:
                last_try = now
                text = buf.decode("utf-8", errors="ignore")
                try:
                    _ = _ensure_contact_info_json(text)
                    # Got JSON; attempt to terminate nicely
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    return text
                except Exception:
                    pass

        # Timeout or no JSON found; terminate and return what we have
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=1)
        except Exception:
            pass
        return buf.decode("utf-8", errors="ignore")
    finally:
        try:
            os.close(master_fd)
        except Exception:
            pass


def get_or_refresh_node_info(
    name: str,
    max_age_seconds: int = 3600,
) -> Tuple[Dict[str, Any], timezone.datetime]:
    """
    Return cached info if fresh; otherwise refresh by running command.

    Saves refreshed results to DB.
    """
    now = timezone.now()
    cutoff = now - timedelta(seconds=max_age_seconds)

    latest: Optional[NodeInfo] = NodeInfo.objects.filter(name=name).order_by("-fetched_at").first()

    # Helper: perform background refresh (base infos and/or extras) without blocking response
    def _spawn_background_refresh(refresh_base: bool, base_data: Optional[Dict[str, Any]] = None) -> None:
        global _last_extras_refresh_started, _last_base_refresh_started
        now_m = time.monotonic()
        if refresh_base:
            if now_m - _last_base_refresh_started < _BASE_REFRESH_MIN_INTERVAL_S:
                return
            _last_base_refresh_started = now_m
        else:
            if now_m - _last_extras_refresh_started < _EXTRAS_REFRESH_MIN_INTERVAL_S:
                return
            _last_extras_refresh_started = now_m
        def _job():
            try:
                info = base_data if base_data is not None else None
                if refresh_base or info is None:
                    try:
                        info = _run_info_command(name)
                    except Exception:
                        info = base_data or {}
                # Enrich with extras (self telemetry + device info)
                try:
                    st = _run_self_telemetry()
                    if isinstance(st, dict):
                        info["self_telemetry"] = st
                except Exception:
                    pass
                try:
                    dv = _run_version_info()
                    if isinstance(dv, dict):
                        info["device_info"] = dv
                except Exception:
                    pass
                data_name = (info or {}).get("name") or name
                NodeInfo.objects.create(name=data_name, data=info or {}, fetched_at=timezone.now())
            except Exception:
                pass
            finally:
                try:
                    # Ensure thread DB connection is not leaked
                    from django.db import connection as _conn  # local import to avoid top-level cost
                    _conn.close()
                except Exception:
                    pass

        try:
            t = threading.Thread(target=_job, daemon=True)
            t.start()
        except Exception:
            pass

    if latest and latest.fetched_at >= cutoff:
        # Return cached data immediately; trigger non-blocking extras update
        data = dict(latest.data or {})
        _spawn_background_refresh(refresh_base=False, base_data=data)
        return data, latest.fetched_at

    # If we have a stale cached entry, return it immediately and refresh in background
    if latest and latest.fetched_at < cutoff:
        data = dict(latest.data or {})
        _spawn_background_refresh(refresh_base=True)
        return data, latest.fetched_at

    # No cached entry: perform a blocking initial fetch
    data = _run_info_command(name)
    # Enrich with extras inline for the very first fetch
    try:
        st = _run_self_telemetry()
        if isinstance(st, dict):
            data["self_telemetry"] = st
    except Exception:
        pass
    try:
        dv = _run_version_info()
        if isinstance(dv, dict):
            data["device_info"] = dv
    except Exception:
        pass
    data_name = data.get("name") or name
    obj = NodeInfo.objects.create(name=data_name, data=data, fetched_at=now)
    return obj.data, obj.fetched_at


def send_chat_message(name: str, text: str, client_id: Optional[str] = None) -> str:
    """Send a chat message via the interactive meshcore session and persist as outgoing.

    Returns a short status string from the CLI output (best-effort).
    """
    name = (name or "").strip()
    text = (text or "").strip()
    if not name:
        raise ValueError("name is required")
    if not text:
        raise ValueError("text is required")

    # Sanitize: remove newlines and control separators to keep a single-line command
    text_clean = text.replace("\n", " ").replace("\r", " ").replace("🭨", " ").strip()
    # Quote the name to tolerate spaces/specials; escape quotes inside the name
    qname = '"' + name.replace('"', '\\"') + '"'

    # Prefer explicit shell template if provided
    cmd_tpl = (os.getenv("MESH_MSG_COMMAND") or "").strip()
    if cmd_tpl:
        cmd = cmd_tpl.format(name=name, text=text_clean)
        proc = subprocess.run(["/bin/sh", "-lc", cmd], capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            raise RuntimeError(f"msg command failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
        output = proc.stdout or ""
        _extract_and_persist_chats(output)
    else:
        # One-shot JSON via meshcore-cli; quote message as a single token.
        qtext = '"' + text_clean.replace('"', '\\"') + '"'
        mesh_cmd = f"msg {qname} {qtext}"
        try:
            stdout, data = _exec_cli_json(mesh_cmd)
            output = stdout
        except Exception:
            # Fallback to plain text mode
            meshcore_bin = _meshcore_bin()
            target = _meshcore_target()
            proc = subprocess.run([meshcore_bin, "-t", target, mesh_cmd], capture_output=True, text=True, timeout=15)
            if proc.returncode != 0:
                raise RuntimeError(f"msg failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
            output = proc.stdout or ""
        _extract_and_persist_chats(output)

    # Lightweight status heuristic from CLI output
    status_text = output or ""
    low = status_text.lower()
    derived_status = "sent"
    if any(k in low for k in ("deliver", "ack", "acknowledged", "delivered")):
        derived_status = "delivered"

    # Persist outgoing message immediately (do not rely on CLI echo)
    contact = Contact.objects.filter(name=name).order_by("-last_seen").first()
    try:
        Message.objects.create(
            contact=contact,
            name=name,
            public_key=contact.public_key if contact else None,
            direction="out",
            text=text_clean,
            ts=timezone.now(),
            raw=output or "",
            status=derived_status,
            client_id=client_id,
        )
    except Exception:
        pass

    # Return last non-empty line as status, if any
    lines = [ln.strip() for ln in (output or "").splitlines()]
    status = ""
    for ln in reversed(lines):
        if ln:
            status = ln
            break
    return status


# --- Automations ------------------------------------------------------------
try:  # optional import for MQTT publish support
    import paho.mqtt.client as mqtt  # type: ignore
except Exception:  # pragma: no cover
    mqtt = None


def _render_template(tpl: str, ctx: Dict[str, Any]) -> str:
    """Very small, safe templating: replaces {key} or {1}..{n} with values in ctx.

    Unknown keys resolve to empty string. Double braces can be used to escape.
    """
    if not tpl:
        return ""

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        try:
            if key.isdigit():
                return str(ctx.get(int(key), ""))
            return str(ctx.get(key, ""))
        except Exception:
            return ""

    s = tpl.replace("{{", "{").replace("}}", "}")
    return re.sub(r"\{([^{}]+)\}", repl, s)


def _match_rule(rule: AutomationRule, *, name: str, public_key: Optional[str], direction: str, text: str) -> Optional[Dict[str, Any]]:
    if not rule.enabled:
        return None
    if rule.only_incoming and direction != "in":
        return None
    if rule.from_name and (name or "").strip().lower() != rule.from_name.strip().lower():
        return None
    if rule.from_public_key and (public_key or "").strip().lower() != rule.from_public_key.strip().lower():
        return None

    t = text if rule.case_sensitive else text.lower()
    p = rule.pattern if rule.case_sensitive else rule.pattern.lower()

    groups: List[str] = []
    matched = False
    if rule.match_type == AutomationRule.MATCH_EQUALS:
        matched = t == p
    elif rule.match_type == AutomationRule.MATCH_PREFIX:
        matched = t.startswith(p)
        if matched:
            groups = [t[len(p):].lstrip()]
    elif rule.match_type == AutomationRule.MATCH_CONTAINS:
        matched = p in t
    elif rule.match_type == AutomationRule.MATCH_REGEX:
        flags = 0 if rule.case_sensitive else re.IGNORECASE
        try:
            m = re.search(rule.pattern, text, flags)
        except re.error:
            m = None
        if m:
            matched = True
            groups = list(m.groups(default=""))
    else:
        matched = False

    if not matched:
        return None

    ctx: Dict[str, Any] = {
        "name": name,
        "public_key": public_key or "",
        "text": text,
        "direction": direction,
        0: text,
    }
    for i, g in enumerate(groups, start=1):
        ctx[i] = g
    return ctx


def _mqtt_publish(topic: str, payload: str) -> Dict[str, Any]:
    if mqtt is None:
        raise RuntimeError("MQTT support not installed (paho-mqtt)")
    cfg = MQTTConfig.objects.order_by('-id').first()
    if not cfg or not cfg.server:
        raise RuntimeError("MQTT server not configured")

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    if cfg.username:
        client.username_pw_set(cfg.username, cfg.password or None)
    if cfg.use_tls:
        import ssl
        client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        client.tls_insecure_set(False)

    client.connect(cfg.server, cfg.port, keepalive=10)
    client.loop_start()
    try:
        info = client.publish(topic, payload=payload, qos=0, retain=False)
        try:
            info.wait_for_publish(timeout=5.0)
        except Exception:
            pass
        rc = getattr(info, 'rc', 0)
        return {"rc": rc, "mid": getattr(info, 'mid', None)}
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass


def evaluate_automations_for_message(*, name: str, public_key: Optional[str], direction: str, text: str, dry_run: bool = False) -> List[Dict[str, Any]]:
    """Evaluate rules for a message and optionally execute actions.

    Returns list of results with rule metadata and action results.
    """
    results: List[Dict[str, Any]] = []
    qs = AutomationRule.objects.filter(enabled=True).order_by("-priority", "id")
    now = timezone.now()
    for rule in qs:
        ctx = _match_rule(rule, name=name, public_key=public_key, direction=direction, text=text)
        if not ctx:
            continue
        # Cooldown
        if rule.cooldown_seconds and rule.last_triggered_at:
            delta = (now - rule.last_triggered_at).total_seconds()
            if delta < rule.cooldown_seconds:
                results.append({
                    "rule_id": rule.id,
                    "name": rule.name,
                    "matched": True,
                    "skipped": True,
                    "reason": f"cooldown {int(rule.cooldown_seconds - delta)}s remaining",
                })
                if rule.stop_processing:
                    break
                continue

        action_result: Dict[str, Any] = {"executed": False}
        if rule.action_type == AutomationRule.ACTION_AUTORESPONSE:
            resp = _render_template(rule.response_text, ctx)
            action_result = {"type": "autoresponse", "text": resp}
            if not dry_run and resp.strip():
                try:
                    send_chat_message(name=name, text=resp)
                    action_result["executed"] = True
                except Exception as e:
                    action_result["error"] = str(e)
        elif rule.action_type == AutomationRule.ACTION_MQTT:
            topic = _render_template(rule.mqtt_topic, ctx)
            payload = _render_template(rule.mqtt_payload, ctx)
            action_result = {"type": "mqtt", "topic": topic, "payload": payload}
            if not dry_run and topic.strip():
                try:
                    pub = _mqtt_publish(topic, payload)
                    action_result.update({"executed": True, "rc": pub.get("rc"), "mid": pub.get("mid")})
                except Exception as e:
                    action_result["error"] = str(e)
        else:
            action_result = {"type": rule.action_type, "error": "unsupported action"}

        try:
            if not dry_run:
                rule.last_triggered_at = timezone.now()
                rule.save(update_fields=["last_triggered_at", "updated_at"])
        except Exception:
            pass

        results.append({
            "rule_id": rule.id,
            "name": rule.name,
            "matched": True,
            "action": action_result,
        })
        if rule.stop_processing:
            break
    return results


def _persist_msg_event_obj(ev: Dict[str, Any]) -> bool:
    """Persist a single message event object from meshcore-cli JSON.

    Returns True if a row was inserted, False otherwise.
    """
    if not isinstance(ev, dict):
        return False
    typ = ev.get("type")
    text = (ev.get("text") or "").strip()
    if not text:
        return False

    name = None
    contact = None
    public_key = None

    if typ == "PRIV":
        prefix = ev.get("pubkey_prefix") or ev.get("pubkey") or ev.get("public_key")
        if isinstance(prefix, str) and prefix:
            try:
                contact = Contact.objects.filter(public_key__startswith=prefix).order_by("-last_seen").first()
                if contact:
                    public_key = contact.public_key
                    name = contact.name or name
            except Exception:
                pass
        # Fallback name: prefer provided name field if any, else use prefix
        if not name:
            name = (ev.get("name") or prefix or "").strip() or "<unknown>"
    elif typ == "CHAN":
        idx = ev.get("channel_idx")
        if idx == 0:
            name = "public"
        elif isinstance(idx, int):
            name = f"ch{idx}"
        else:
            name = "channel"
    else:
        # Unknown type; attempt generic
        name = (ev.get("name") or "").strip() or "<unknown>"

    # De-dup burst: avoid storing identical recent entries
    try:
        cutoff = timezone.now() - timedelta(seconds=3)
        if Message.objects.filter(direction="in", name=name, text=text, ts__gte=cutoff).exists():
            return False
    except Exception:
        pass

    try:
        Message.objects.create(
            contact=contact,
            name=name,
            public_key=public_key,
            direction="in",
            text=text,
            ts=timezone.now(),
            raw=json.dumps(ev, ensure_ascii=False),
        )
        return True
    except Exception:
        return False


def sync_unread_messages() -> int:
    """Fetch all unread messages via one-shot JSON command and persist them.

    Returns number of messages stored.
    """
    try:
        stdout, data = _exec_cli_json("sync_msgs")
    except Exception:
        # In case of error, try plain text as last resort (unlikely in JSON mode)
        return 0
    count = 0
    if isinstance(data, list):
        for ev in data:
            if _persist_msg_event_obj(ev):
                count += 1
    elif isinstance(data, dict):
        if _persist_msg_event_obj(data):
            count += 1
    return count


def _run_req_status_command(name: str) -> Optional[Dict[str, Any]]:
    """Request status for a contact, persist useful telemetry (e.g., rssi/snr).

    Returns parsed dict on success; None on error.
    """
    # Prefer blocking/synchronous variant for robustness
    try:
        stdout, data = _exec_cli_json(f'req_bstatus "{name}"')
        _extract_and_persist_chats(stdout)
        if isinstance(data, dict):
            data.setdefault("name", name)
            if any(k in data for k in ("rssi", "snr", "adv_lat", "adv_lon", "type", "flags", "level", "battery", "battery_percent", "battery_mv")):
                _persist_contact_info(data)
            return data
    except Exception:
        pass

    # Fallback to event-based variant
    try:
        stdout, data = _exec_cli_json(f'req_status "{name}"')
        _extract_and_persist_chats(stdout)
        if isinstance(data, dict):
            data.setdefault("name", name)
            if any(k in data for k in ("rssi", "snr", "adv_lat", "adv_lon", "type", "flags", "level", "battery", "battery_percent", "battery_mv")):
                _persist_contact_info(data)
            return data
    except Exception:
        return None
    return None


def _run_req_telemetry_command(name: str) -> Optional[Dict[str, Any]]:
    """Request telemetry for a contact via req_telemetry and persist useful fields.

    Returns parsed dict on success; None on error.
    """
    try:
        stdout, data = _exec_cli_json(f'req_telemetry "{name}"')
        _extract_and_persist_chats(stdout)
        if isinstance(data, dict):
            data.setdefault("name", name)
            if any(k in data for k in ("rssi", "snr", "adv_lat", "adv_lon", "type", "flags", "last_advert", "battery", "battery_percent", "battery_mv")):
                _persist_contact_info(data)
            return data
    except Exception:
        return None
    return None
