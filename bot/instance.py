"""Single-writer guard for the logs/ volume.

Liara starts the new container before it stops the old one, and both mount the same logs disk,
so for a short while two bots run side by side (seen as "state_*.json.tmp" rename races). In live
mode that would mean two engines placing orders. The newest instance claims the lock at start-up;
an older instance that finds someone else's id in the lock stops itself.
"""
from __future__ import annotations

import os
import socket
import time
import uuid


class InstanceLock:
    def __init__(self, path: str):
        self.path = path
        self.id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"

    def claim(self):
        tmp = f"{self.path}.{self.id}.tmp"
        with open(tmp, "w") as f:
            f.write(f"{self.id} {time.time():.0f}\n")
        os.replace(tmp, self.path)

    def still_mine(self) -> bool:
        try:
            return open(self.path).read().split()[0] == self.id
        except (OSError, IndexError):
            return True             # unreadable lock: keep running rather than stop trading
