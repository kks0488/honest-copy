"""Daily cap on model calls, stored in a small JSON file.

The count resets at midnight UTC. The file holds only a date and a number.
"""

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl  # Linux / macOS (Spaces run on Linux)
except ImportError:  # pragma: no cover
    fcntl = None

DEFAULT_DAILY_CAP = 40


def default_usage_path() -> Path:
    env = os.environ.get("BEAM_USAGE_FILE")
    if env:
        return Path(env)
    data = Path("/data")  # persistent storage on Spaces, when enabled
    if data.is_dir() and os.access(data, os.W_OK):
        return data / "beam_usage.json"
    return Path(__file__).resolve().parent.parent / ".usage" / "beam_usage.json"


def daily_cap_from_env() -> int:
    try:
        return max(0, int(os.environ.get("BEAM_DAILY_CALL_CAP", str(DEFAULT_DAILY_CAP))))
    except ValueError:
        return DEFAULT_DAILY_CAP


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class DailyBudget:
    _thread_lock = threading.Lock()

    def __init__(self, path: str | os.PathLike | None = None, cap: int | None = None, today=_today):
        self.path = Path(path) if path else default_usage_path()
        self.cap = daily_cap_from_env() if cap is None else cap
        self._today = today

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            with open(self.path, "a+", encoding="utf-8") as fh:
                if fcntl:
                    fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    yield fh
                finally:
                    if fcntl:
                        fcntl.flock(fh, fcntl.LOCK_UN)

    def _read(self, fh) -> int:
        fh.seek(0)
        try:
            data = json.loads(fh.read() or "{}")
        except json.JSONDecodeError:
            data = {}
        if data.get("date") != self._today():
            return 0
        try:
            return max(0, int(data.get("calls", 0)))
        except (TypeError, ValueError):
            return 0

    def _write(self, fh, calls: int) -> None:
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps({"date": self._today(), "calls": calls}))
        fh.flush()

    def used(self) -> int:
        with self._locked() as fh:
            return self._read(fh)

    def remaining(self) -> int:
        return max(0, self.cap - self.used())

    def try_spend(self, n: int = 1) -> bool:
        """Reserve ``n`` calls. Returns False (and reserves nothing) if that would pass the cap."""
        with self._locked() as fh:
            used = self._read(fh)
            if used + n > self.cap:
                return False
            self._write(fh, used + n)
            return True
