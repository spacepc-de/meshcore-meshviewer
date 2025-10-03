import os
import pty
import fcntl
import termios
import struct
import select
import shlex
import subprocess
import threading
import time
import re
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from .models import Message, Contact
import logging


ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class MeshCoreSession:
    """Singleton-like manager for a single interactive meshcore-cli session.

    - Ensures only one PTY-based session to the device is open.
    - Serializes command writes via a lock (implicit queueing).
    - Continuously reads output in a background thread and stores incoming chat lines.
    - Provides a run_json_command helper that waits for JSON blob to appear after issuing a line.
    """

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._master_fd: Optional[int] = None
        self._buffer = ""
        self._buf_lock = threading.Lock()
        self._buf_cond = threading.Condition(self._buf_lock)
        self._cmd_lock = threading.Lock()  # serialize commands
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        target = os.getenv("MESHCORE_TARGET", "").strip()
        meshcore_bin = os.getenv("MESHCORE_CLI", "meshcore-cli").strip() or "meshcore-cli"
        if not target:
            raise RuntimeError("MESHCORE_TARGET not configured")

        master_fd, slave_fd = pty.openpty()
        try:
            # Ensure a sane terminal size to avoid ZeroDivisionError in CLI UI code
            try:
                rows, cols = 40, 120
                winsz = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsz)
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsz)
            except Exception:
                pass

            env = os.environ.copy()
            env.setdefault("COLUMNS", "120")
            env.setdefault("LINES", "40")
            env.setdefault("TERM", "xterm-256color")
            self._proc = subprocess.Popen(
                [meshcore_bin, "-t", target],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                text=False,
                env=env,
            )
        finally:
            os.close(slave_fd)

        self._master_fd = master_fd
        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, name="meshcore-reader", daemon=True)
        self._reader_thread.start()

    def ensure_started(self) -> None:
        if not self._running or not self._proc or self._proc.poll() is not None:
            self._running = False
            self.start()

    def is_alive(self) -> bool:
        """Return True if the interactive meshcore process is alive."""
        try:
            return bool(self._running and self._proc and self._proc.poll() is None)
        except Exception:
            return False

    def stop(self) -> None:
        self._running = False
        try:
            if self._proc:
                self._proc.terminate()
        except Exception:
            pass
        try:
            if self._master_fd is not None:
                os.close(self._master_fd)
        except Exception:
            pass
        self._proc = None
        self._master_fd = None

    def _reader_loop(self) -> None:
        logger = logging.getLogger("meshcore.session")
        fd = self._master_fd
        if fd is None:
            return
        partial = b""
        while self._running:
            try:
                r, _, _ = select.select([fd], [], [], 0.2)
                if fd not in r:
                    continue
                chunk = os.read(fd, 4096)
                if not chunk:
                    time.sleep(0.05)
                    continue
                partial += chunk
                # Normalize to text
                text = partial.decode("utf-8", errors="ignore")
                # Keep last complete lines in 'lines', retain remainder in 'partial'
                if not text:
                    continue
                # Split preserving remainder
                if text.endswith("\n"):
                    lines_text = text
                    partial = b""
                else:
                    last_nl = text.rfind("\n")
                    if last_nl == -1:
                        # no complete line yet, keep accumulating
                        continue
                    lines_text = text[: last_nl + 1]
                    partial = text[last_nl + 1 :].encode("utf-8", errors="ignore")

                # Strip ANSI and append to buffer
                cleaned = ANSI_RE.sub("", lines_text)
                with self._buf_lock:
                    self._buffer += cleaned
                    self._buf_cond.notify_all()

                # Log and parse each line
                for line in cleaned.splitlines():
                    if line.strip():
                        try:
                            logger.info(line.rstrip())
                        except Exception:
                            pass
                    self._maybe_store_chat_line(line)
            except Exception:
                time.sleep(0.1)

    # Delimiter pattern for the start of a chat message: "Name (D):"
    NAME_DELIM_RE = re.compile(r"([^\(\n🭨]+?)\s*\(D\):\s*")

    def _maybe_store_chat_line(self, line: str) -> None:
        # Be tolerant: a single console line may contain multiple chat messages
        # and prompt fragments; scan for all chat occurrences.
        if not line:
            return
        # Collect prompt names (e.g., 'JOST_DEV' in 'JOST_DEV🭨') to trim from tail
        try:
            prompt_names = re.findall(r"(?<!\w)([A-Za-z0-9][A-Za-z0-9_-]{0,63})🭨", line)
        except Exception:
            prompt_names = []

        # Find all "(D):" delimiters and determine names/texts robustly
        delim_re = re.compile(r"\(D\):\s*")
        delims = list(delim_re.finditer(line))
        if not delims:
            return

        # Known contact names to disambiguate concatenations like 'HalloJOST (D):'
        try:
            known_names = list(Contact.objects.exclude(name="").values_list("name", flat=True))
        except Exception:
            known_names = []
        known_names = sorted(set(n for n in known_names if isinstance(n, str)), key=len, reverse=True)

        # Pre-compute prompt positions to help bound name search
        prompt_positions = [m.start() for m in re.finditer("🭨", line)]

        # First pass: compute name and name_start for each delimiter
        parts = []  # list of dict(name, name_start, text_start, next_name_start)
        for i, d in enumerate(delims):
            name_end = d.start()
            # Trim any whitespace right before the '(D):' token
            while name_end > 0 and line[name_end - 1].isspace():
                name_end -= 1
            text_start = d.end()
            # Search window for the name start: from after last delimiter or after last prompt to name_end
            left_bound = 0
            if i > 0:
                left_bound = max(left_bound, delims[i - 1].end())
            if prompt_positions:
                # last prompt before name_end
                left_bound = max(left_bound, max([p + 1 for p in prompt_positions if p < name_end], default=0))
            window = line[left_bound:name_end].rstrip()
            name = None
            # Prefer known names that are a suffix of the window
            for kn in known_names:
                if window.endswith(kn):
                    name = kn
                    name_start = name_end - len(kn)
                    break
            if not name:
                # Fallback: take the trailing token up to 64 chars as name (best-effort)
                tail = window[-64:]
                # strip anything before the last whitespace or punctuation if present
                # but if none present, take the last 32 letters/digits/ _-
                m_tail = re.search(r"([A-Za-z0-9 _\-]{1,64})\s*$", tail)
                if m_tail:
                    cand = m_tail.group(1).strip()
                    if cand:
                        name = cand
                        name_start = name_end - len(cand)
                if not name:
                    # As a last resort, use up to 16 chars right before '(D):'
                    cand = window[-16:].strip()
                    name = cand
                    name_start = name_end - len(cand)

            parts.append({
                "name": name or "",
                "name_start": name_start,
                "text_start": text_start,
            })

        # Second pass: determine text_end for each part and persist
        for i, part in enumerate(parts):
            name = part["name"].strip()
            if not name:
                continue
            text_start = part["text_start"]
            next_name_start = parts[i + 1]["name_start"] if i + 1 < len(parts) else None
            sep_pos = line.find("🭨", text_start)
            text_end = len(line)
            if next_name_start is not None:
                text_end = min(text_end, next_name_start)
            if sep_pos != -1:
                text_end = min(text_end, sep_pos)
            text = line[text_start:text_end].strip()
            if not text:
                continue
            if prompt_names:
                for pn in prompt_names:
                    if pn and text.endswith(pn):
                        text = text[: -len(pn)].rstrip()
                        break
            if not text:
                continue

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
                    raw=line,
                )
            except Exception:
                pass

    def run_json_command(self, line: str, timeout_s: float = 5.0):
        self.ensure_started()
        if self._master_fd is None:
            raise RuntimeError("mesh session not started")
        with self._cmd_lock:
            start = time.time()
            with self._buf_lock:
                start_len = len(self._buffer)
            # Write the command line
            os.write(self._master_fd, (line + "\n").encode("utf-8", errors="ignore"))

            # Wait for a JSON object/array to appear after start_len
            while time.time() - start < timeout_s:
                with self._buf_lock:
                    segment = self._buffer[start_len:]
                try:
                    data = self._extract_json(segment)
                    if data is not None:
                        return data
                except Exception:
                    pass
                with self._buf_lock:
                    self._buf_cond.wait(timeout=0.1)
            raise TimeoutError("Timeout waiting for JSON response")

    def run_text_command(self, line: str, dwell_s: float = 0.5, max_wait_s: float = 3.0, wait_for_prompt: bool = True) -> str:
        """Send a command and return the new text produced after the write.

        - max_wait_s: overall cap
        - dwell_s: return once there's been at least dwell_s with no new bytes
        """
        self.ensure_started()
        if self._master_fd is None:
            raise RuntimeError("mesh session not started")
        with self._cmd_lock:
            with self._buf_lock:
                start_len = len(self._buffer)
            os.write(self._master_fd, (line + "\n").encode("utf-8", errors="ignore"))

            start = time.time()
            last_size = start_len
            last_change = time.time()
            saw_prompt = False
            while True:
                now = time.time()
                if now - start >= max_wait_s:
                    break
                with self._buf_lock:
                    cur_len = len(self._buffer)
                if cur_len != last_size:
                    last_size = cur_len
                    last_change = now
                    if wait_for_prompt:
                        seg = self._buffer[start_len:]
                        if self._has_prompt(seg):
                            saw_prompt = True
                else:
                    if (not wait_for_prompt or saw_prompt) and (now - last_change >= dwell_s):
                        break
                with self._buf_lock:
                    self._buf_cond.wait(timeout=0.1)

            with self._buf_lock:
                segment = self._buffer[start_len:]
            return segment

    @staticmethod
    def _has_prompt(text: str) -> bool:
        # Detect a prompt line ending with the special separator, e.g., "JOST_DEV🭨"
        for ln in text.splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.endswith("🭨") and not s.endswith("🭨contacts") and not s.endswith("🭨infos"):
                return True
        return False

    @staticmethod
    def _extract_json(text: str):
        import json
        s = text.strip()
        # Try object
        i = s.find("{")
        j = s.rfind("}")
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(s[i : j + 1])
            except Exception:
                pass
        # Try array
        i = s.find("[")
        j = s.rfind("]")
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(s[i : j + 1])
            except Exception:
                pass
        return None


_SESSION: Optional[MeshCoreSession] = None
_SESSION_LOCK = threading.Lock()


def get_session() -> MeshCoreSession:
    global _SESSION
    with _SESSION_LOCK:
        if _SESSION is None:
            _SESSION = MeshCoreSession()
            # Don't auto-start here to allow missing env to raise only when used
        return _SESSION
