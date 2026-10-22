"""Market data for the users' bots: one fetch per tick serves every user (cost does not grow with users).

wallex : live top of book of every Toman market in one request (/v2/depth/all) + USDT/TMN hourly candles
         for the entry rule (the same regime rule as the engine: USDT/TMN 48 h change >= +1%).
replay : offline demo on the real hourly Wallex data shipped in data/hourly.json, played back at
         REPLAY_SPEED x real time (back and forth, so prices never jump). Shown with a banner in the UI.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

from .settings import ROOT, settings

log = logging.getLogger("portal.market")

REGIME_EVERY_S = 600


def _regime(closes_by_age: dict[int, float], last: float, threshold: float) -> dict:
    def ch(h):
        old = closes_by_age.get(h)
        return round((last / old - 1) * 100, 2) if old else None
    c48 = ch(48)
    return {"usdt_tmn": round(last), "ch6_pct": ch(6), "ch24_pct": ch(24), "ch48_pct": c48,
            "threshold_pct": threshold, "on": c48 is not None and c48 >= threshold}


class WallexFeed:
    source = "wallex"

    def __init__(self):
        import sys
        sys.path.insert(0, ROOT)
        from bot.wallex_client import WallexClient     # the engine's own client (retries, 429 handling)
        self.client = WallexClient(None, per_sec=2, max_retries=2)
        self.regime: dict = {}
        self.last_regime = 0.0

    def snapshot(self, threshold: float) -> dict:
        books = self.client.depth_all()
        prices = {}
        for sym, b in books.items():
            if sym.endswith("TMN") and b["bids"] and b["asks"]:
                prices[sym[:-3]] = {"bid": b["bids"][0][0], "ask": b["asks"][0][0]}
        now = time.time()
        if now - self.last_regime > REGIME_EVERY_S or not self.regime:
            c = self.client.candles("USDTTMN", "60", now - 52 * 3600, now)
            if c["t"]:
                by_age = {}
                for t, close in zip(c["t"], c["c"]):            # t = open of the hourly candle
                    by_age.setdefault(int(round((now - t - 3600) / 3600)), close)
                last = (prices.get("USDT") or {}).get("bid") or c["c"][-1]
                self.regime = _regime(by_age, last, threshold)
                self.last_regime = now
        return {"ts": now, "data_ts": now, "prices": prices, "regime": self.regime, "source": self.source}


class ReplayFeed:
    source = "replay"
    HALF_SPREAD = 0.0015

    def __init__(self, path=os.path.join(ROOT, "data", "hourly.json"), speed=None):
        raw = json.load(open(path, encoding="utf-8"))
        self.series = {}
        for sym, d in raw.items():
            if sym.endswith("TMN"):
                self.series[sym[:-3]] = (d["t0"], d["t"], d["c"])
        t0, t, _ = self.series["USDT"]
        self.start = t0 + 49 * 3600                     # need 48 h of history for the entry rule
        self.span = t0 + t[-1] * 3600 - self.start
        self.speed = speed if speed is not None else settings.replay_speed

    def data_time(self, now: float) -> float:
        x = (now * self.speed) % (2 * self.span)        # triangle wave: forward, then backward
        return self.start + (x if x <= self.span else 2 * self.span - x)

    def close_at(self, asset: str, ts: float) -> float | None:
        t0, t, c = self.series[asset]
        h = (ts - t0) / 3600
        i = int(h)
        if i < 0 or i >= len(c) - 1:
            return c[min(max(i, 0), len(c) - 1)]
        return c[i] + (c[i + 1] - c[i]) * (h - i)

    def snapshot(self, threshold: float, now: float | None = None) -> dict:
        now = now or time.time()
        dt = self.data_time(now)
        prices = {}
        for a in self.series:
            mid = self.close_at(a, dt)
            if mid:
                prices[a] = {"bid": mid * (1 - self.HALF_SPREAD), "ask": mid * (1 + self.HALF_SPREAD)}
        last = self.close_at("USDT", dt)
        by_age = {h: self.close_at("USDT", dt - h * 3600) for h in (6, 24, 48)}
        return {"ts": now, "data_ts": dt, "prices": prices, "regime": _regime(by_age, last, threshold),
                "source": self.source}


class Market:
    """Thread-safe holder of the latest snapshot; the worker refreshes it, the web layer reads it."""

    def __init__(self):
        self.lock = threading.Lock()
        self.snap: dict = {}
        self.error = ""
        self.feed = None

    def _feed(self):
        if self.feed is None:
            self.feed = ReplayFeed() if settings.market_source == "replay" else WallexFeed()
        return self.feed

    def threshold(self) -> float:
        return float((settings.engine_config.get("portfolio") or {}).get("regime_full_pct", 1.0))

    def refresh(self) -> dict:
        try:
            s = self._feed().snapshot(self.threshold())
            with self.lock:
                self.snap, self.error = s, ""
        except Exception as e:                          # noqa: BLE001 — keep the last good snapshot
            log.warning("market refresh failed: %s", e)
            with self.lock:
                self.error = str(e)[:200]
        return self.get()

    def get(self) -> dict:
        with self.lock:
            s = dict(self.snap)
            s["error"] = self.error
        return with_freshness(s)


def with_freshness(snap: dict | None) -> dict:
    s = dict(snap or {})
    s["fresh"] = bool(s.get("ts")) and time.time() - s["ts"] < max(180, 3 * settings.tick_seconds)
    return s


market = Market()
