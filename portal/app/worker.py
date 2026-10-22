"""Background loops (one app instance; for more users run `python -m portal.app.worker` as its own process
and set RUN_WORKER=0 on the web instances).

  market loop  : every TICK_SECONDS one market snapshot, then one step of every running paper bot
  founder loop : every FOUNDER_POLL_S the real Wallex account + the real bot's telemetry
"""
from __future__ import annotations

import logging
import threading
import time

from sqlalchemy import select

from . import simulator
from .db import BotAccount, EquitySnapshot, SessionLocal, User, init_db, kv_get, kv_set, now
from .market import market
from .settings import settings
from .telemetry import bot_telemetry, wallex_account

log = logging.getLogger("portal.worker")
BATCH = 200


def step_all_bots(snap: dict) -> int:
    if not snap.get("fresh"):
        return 0
    n, last_id = 0, 0
    while True:
        with SessionLocal() as db:
            bots = db.scalars(select(BotAccount).where(BotAccount.status == "running", BotAccount.mode == "paper",
                                                       BotAccount.id > last_id).order_by(BotAccount.id).limit(BATCH)).all()
            if not bots:
                return n
            for bot in bots:
                try:
                    ctx = simulator.step(bot, snap)
                    db.add_all(ctx.trades + ctx.events)
                    s = simulator.maybe_snapshot(bot, snap["prices"], settings.snapshot_every_s)
                    if s:
                        db.add(s)
                    n += 1
                except Exception:                               # noqa: BLE001 — one bad bot must not stop the rest
                    log.exception("bot %s step failed", bot.id)
                last_id = bot.id
            db.commit()


def record_founder(wallex: dict, tele: dict):
    """Persist the founder picture (the web process may be a different process than this worker)."""
    with SessionLocal() as db:
        kv_set(db, "wallex", wallex)
        kv_set(db, "bot", tele)
        f = db.scalars(select(User).where(User.role == "founder")).first()
        bot = db.scalars(select(BotAccount).where(BotAccount.user_id == f.id)).first() if f else None
        if bot and wallex.get("ok") and now() - (bot.last_snapshot_at or 0) >= 60:
            s = wallex["by_sleeve"]
            db.add(EquitySnapshot(bot_id=bot.id, ts=now(), equity_tmn=wallex["equity_tmn"],
                                  low_tmn=s["low"] + s["cash"] + s["other"], medium_tmn=s["medium"], high_tmn=s["high"]))
            bot.last_snapshot_at = now()
        if bot_telemetry.remember:
            kv_set(db, "bot_remember", bot_telemetry.remember)
        db.commit()


class Loop(threading.Thread):
    def __init__(self, name, every, fn):
        super().__init__(name=name, daemon=True)
        self.every, self.fn = every, fn
        self.stop = threading.Event()

    def run(self):
        while not self.stop.is_set():
            t0 = time.time()
            try:
                self.fn()
            except Exception:                                   # noqa: BLE001
                log.exception("%s failed", self.name)
            self.stop.wait(max(1.0, self.every - (time.time() - t0)))


def market_tick():
    snap = market.refresh()
    with SessionLocal() as db:
        kv_set(db, "market", {k: v for k, v in snap.items() if k != "fresh"})
        db.commit()
    step_all_bots(snap)


def founder_tick():
    w = wallex_account.refresh()
    t = bot_telemetry.refresh()
    record_founder(w, t)


def start_loops() -> list[Loop]:
    with SessionLocal() as db:
        bot_telemetry.remember = kv_get(db, "bot_remember", {}) or {}
    loops = [Loop("market", settings.tick_seconds, market_tick), Loop("founder", settings.founder_poll_s, founder_tick)]
    for x in loops:
        x.start()
    return loops


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    for loop in start_loops():
        loop.join()
