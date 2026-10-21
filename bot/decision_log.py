"""Append-only JSONL decision log: every signal, AI decision, risk veto, order and
fill is recorded with a reason, so every trade can be traced back to its cause."""
from __future__ import annotations

import json
import os
import time
import uuid
import threading


class DecisionLog:
    def __init__(self, path: str, mode: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.mode = mode
        self.lock = threading.Lock()

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    def write(self, event: str, **fields):
        rec = {"ts": round(time.time(), 3),
               "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
               "mode": self.mode, "event": event, **fields}
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with self.lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return rec
