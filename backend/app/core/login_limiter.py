"""
login_limiter.py - In-memory brute-force protection for super admin login.

Tracks failed attempts per (IP, username) key. After MAX_ATTEMPTS failures
within WINDOW_SECONDS, blocks further attempts for LOCKOUT_SECONDS.
"""

import time
from threading import Lock

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5 minutes sliding window
_LOCKOUT_SECONDS = 900  # 15 minutes lockout


class _LoginLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = {}
        self._lock = Lock()

    def _key(self, ip: str, username: str) -> str:
        return f"{ip}:{username.lower()}"

    def check(self, ip: str, username: str) -> tuple[bool, int]:
        """Return (is_blocked, seconds_remaining). Cleans up stale entries."""
        key = self._key(ip, username)
        now = time.monotonic()
        with self._lock:
            timestamps = [t for t in self._attempts.get(key, []) if now - t < _WINDOW_SECONDS]
            self._attempts[key] = timestamps
            if len(timestamps) >= _MAX_ATTEMPTS:
                oldest = timestamps[0]
                remaining = int(_LOCKOUT_SECONDS - (now - oldest))
                return True, max(1, remaining)
            return False, 0

    def record_failure(self, ip: str, username: str) -> None:
        key = self._key(ip, username)
        now = time.monotonic()
        with self._lock:
            timestamps = [t for t in self._attempts.get(key, []) if now - t < _WINDOW_SECONDS]
            timestamps.append(now)
            self._attempts[key] = timestamps

    def clear(self, ip: str, username: str) -> None:
        key = self._key(ip, username)
        with self._lock:
            self._attempts.pop(key, None)


superadmin_login_limiter = _LoginLimiter()
