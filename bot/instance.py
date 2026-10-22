"""Single-writer guard for the logs/ volume.

Liara starts the new container before it stops the old one, and both mount the same logs disk,
so for a short while two bots run side by side (seen as "state_*.json.tmp" rename races). In live
mode that would mean two engines placing orders. The newest instance claims the lock at start-up;
an older instance that finds someone else's id in the lock stops itself. The running instance
refreshes a heartbeat in the lock, and a supervisor in ANOTHER container does not restart its bot
while that heartbeat is fresh (otherwise the two containers would keep superseding each other).
"""
from __future__ import annotations

import os
import socket
import time
import uuid

HOST = socket.gethostname()


class InstanceLock:
    def __init__(self, path: str):
        self.path = path
        self.id = f"{HOST}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._beat = 0.0

    def _write(self):
        tmp = f"{self.path}.{self.id}.tmp"
        with open(tmp, "w") as f:
            f.write(f"{self.id} {HOST} {time.time():.0f}\n")
        os.replace(tmp, self.path)
        self._beat = time.time()

    def claim(self):
        self._write()

    def heartbeat(self, every_s: float = 10.0):
        if time.time() - self._beat >= every_s and self.still_mine():
            self._write()

    def still_mine(self) -> bool:
        try:
            return open(self.path).read().split()[0] == self.id
        except (OSError, IndexError):
            return True             # unreadable lock: keep running rather than stop trading


def held_elsewhere(path: str, fresh_s: float = 45.0) -> str | None:
    """Host of a live bot in another container holding the lock, or None (for the supervisor)."""
    try:
        parts = open(path).read().split()
        lock_host, ts = parts[1], float(parts[2])
    except (OSError, IndexError, ValueError):
        return None
    return lock_host if lock_host != HOST and time.time() - ts < fresh_s else None
