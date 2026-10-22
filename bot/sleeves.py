"""Holding sleeves: the medium- and high-risk strategies of the 3-strategy portfolio.

Evidence (python run.py regime-study, 29 days of hourly Wallex data): Toman prices of USDT and of every
coin rose ~15-19% in 29 days, almost all of it the rial weakening. 27-hour holds entered while USDT/TMN
had risen >= 1% in 48 h, net of fees (0.25% in, 0.30% out), no trailing stop (best risk-adjusted basket
of each class, see STRATEGY.md):
    rial  BTC/ETH              +0.88%  P(loss) 34%  worst -2.93%   (USDT/BTC/ETH +0.74%, USDT only +0.52%)
    beta  PEPE/ADA/LINK        +1.28%  P(loss) 30%  worst -4.28%   (ADA/PEPE/SHIB/DOGE +1.12%)
Outside that regime the same holds LOST, so exposure is gated by the regime (and the AI). Tight stops and
trailing stops cut the winners, so the sleeves only carry a wide disaster stop.

Each sleeve owns a fixed budget (capital_pct of the initial capital), a target weight per asset, a
stop-loss and a trailing stop on the sleeve as a whole. Entries are maker bids at the best bid that
turn into taker orders after `maker_timeout_s`; exits on a stop are taker. USDT can only be traded
while the USDT/TMN market is open (08:00-21:00 Tehran), so a USDT holding is closed by `usdt_exit_at`.
At the end of the challenge the sleeves are sold in steps (RiskManager.wind_down: 4 steps from 4 h before
the end) with maker asks, taker after `wind_down_taker_after_s`; the forced flatten only sells leftovers.
"""
from __future__ import annotations

import logging
from datetime import datetime

from .wallex_client import WallexError

log = logging.getLogger("sleeves")


class HoldingSleeve:
    def __init__(self, name: str, cfg: dict, engine):
        self.name, self.cfg, self.e = name, cfg, engine
        self.capital = engine.cfg["challenge"]["initial_capital_tmn"] * cfg["capital_pct"] / 100
        self.weights = dict(cfg["assets"])
        self.pos: dict[str, dict] = {}         # asset -> {"qty", "cost"}  (bought by THIS sleeve)
        self.orders: dict[str, dict] = {}      # asset -> resting order
        self.realised = 0.0
        self.peak_ret = 0.0
        self.stopped: str | None = None        # reason once a stop closed the sleeve (no re-entry)
        self.scale = 0.0                       # 0..1, set from regime cap and AI decision
        self.last_act = 0.0
        self.last_reweight = 0.0
        self.trim_t0: dict[str, float] = {}    # asset -> when the current trim/wind-down sale started

    # -------------------------------------------------------------- state
    def to_state(self):
        return {"pos": self.pos, "orders": self.orders, "realised": self.realised, "peak_ret": self.peak_ret,
                "stopped": self.stopped, "scale": self.scale, "weights": self.weights,
                "last_reweight": self.last_reweight, "trim_t0": self.trim_t0}

    def from_state(self, s):
        self.pos = s.get("pos") or {}
        self.orders = s.get("orders") or {}
        self.realised = s.get("realised", 0.0)
        self.peak_ret = s.get("peak_ret", 0.0)
        self.stopped = s.get("stopped")
        self.scale = s.get("scale", 0.0)
        self.weights = s.get("weights") or self.weights
        self.last_reweight = s.get("last_reweight", 0.0)
        self.trim_t0 = s.get("trim_t0") or {}

    # ------------------------------------------------------------ helpers
    def assets(self):
        return set(self.weights) | set(self.pos) | set(self.orders)

    def value(self, books) -> tuple[float, float]:
        """(mark value of holdings at best bid, cost of holdings)"""
        v = c = 0.0
        for a, p in self.pos.items():
            b = books.get(f"{a}TMN", {}).get("bids")
            if b and p["qty"] > 0:
                v += p["qty"] * b[0][0]
                c += p["cost"]
        return v, c

    def pnl(self, books) -> float:
        v, c = self.value(books)
        return v - c + self.realised

    def ret(self, books) -> float:
        v, c = self.value(books)
        return (v / c - 1) if c > 0 else 0.0

    def market_open(self, asset, now) -> bool:
        if asset != "USDT":
            return True
        h = datetime.fromtimestamp(now, self.e.risk_tz).hour
        return 8 <= h < 21

    def must_exit(self, asset, now) -> bool:
        if self.e.risk.must_flatten(now):
            return True
        if asset == "USDT":
            return now >= datetime.fromisoformat(self.cfg.get("usdt_exit_at", "2026-10-23T20:00:00+03:30")).timestamp()
        return False

    # -------------------------------------------------------------- fills
    def reconcile(self):
        for a, o in list(self.orders.items()):
            try:
                x = self.e.ex.get(o["cid"])
            except WallexError as ex:
                log.warning("sleeve %s get %s: %s", self.name, o["cid"], ex)
                continue
            exq = float(x.get("executedQty", 0) or 0)
            if exq > o["exec_seen"]:
                q = exq - o["exec_seen"]
                o["exec_seen"] = exq
                fee = self.e.fees.tmn_taker if o.get("taker") else self.e.fees.tmn_maker
                p = self.pos.setdefault(a, {"qty": 0.0, "cost": 0.0})
                if o["side"] == "BUY":
                    p["qty"] += q * (1 - fee)
                    p["cost"] += q * o["price"]
                else:
                    part = p["cost"] * min(1.0, q / p["qty"]) if p["qty"] > 0 else 0.0
                    proceeds = q * o["price"] * (1 - fee)
                    self.realised += proceeds - part
                    p["qty"] = max(0.0, p["qty"] - q)
                    p["cost"] -= part
                self.e.dirty()
                self.e.dlog.write("sleeve_fill", sleeve=self.name, asset=a, side=o["side"], qty=q, price=o["price"],
                                  taker=bool(o.get("taker")), notional_tmn=round(q * o["price"]),
                                  why=o.get("why"))
            if not x.get("active", True):
                self.orders.pop(a, None)

    def cancel(self, a):
        o = self.orders.get(a)
        if o:
            self.e.ex.cancel(o["cid"])
            self.e.dirty()
            self.reconcile()
            self.orders.pop(a, None)

    def place(self, a, side, qty, price, taker, why, now):
        m = self.e.markets[f"{a}TMN"]
        if side == "BUY":                       # never send an order the exchange would reject for lack of Toman
            qty = min(qty, self.e.bal().get("TMN", {}).get("free", 0.0) * 0.98 / price)
        qty = m.round_qty(qty)
        if qty <= 0 or qty < m.min_qty or qty * price < max(m.min_notional, 60_000):
            return
        try:
            o = self.e.ex.place_limit(m, side, qty, price, prefix="S", taker=taker)
        except WallexError as ex:
            self.e.dlog.write("sleeve_order_failed", sleeve=self.name, asset=a, side=side, error=str(ex)[:200])
            return
        self.e.dirty()
        self.orders[a] = {"cid": o["clientOrderId"], "side": side, "price": m.round_price(price, side),
                          "qty": qty, "t": now, "exec_seen": 0.0, "taker": taker, "why": why}
        self.e.dlog.write("sleeve_order", sleeve=self.name, asset=a, side=side, qty=qty,
                          price=m.round_price(price, side), size_tmn=round(qty * price), taker=taker, why=why)

    # ---------------------------------------------------------------- step
    def step(self, books, now):
        self.reconcile()
        r = self.ret(books)
        v, c = self.value(books)
        if c > 0 and not self.stopped:
            self.peak_ret = max(self.peak_ret, r)
            trail_start, trail_gap = self.cfg.get("trail_start_pct", 2.5) / 100, self.cfg.get("trail_gap_pct", 1.0) / 100
            if r < -self.cfg["stop_pct"] / 100:
                self.stopped = f"stop-loss: sleeve {r*100:.2f}% below cost"
            elif self.peak_ret >= trail_start and r <= self.peak_ret - trail_gap:
                self.stopped = f"trailing stop: {r*100:.2f}% after a peak of {self.peak_ret*100:.2f}%"
            if self.stopped:
                self.e.dlog.write("sleeve_stop", sleeve=self.name, why=self.stopped, value_tmn=round(v), cost_tmn=round(c))
        if now - self.last_act < self.cfg.get("act_every_s", 20) and not self.stopped:
            return
        self.last_act = now
        wind = self.e.risk.wind_down(now)
        for a in sorted(self.assets()):
            sym = f"{a}TMN"
            b = books.get(sym)
            if not b or not b["bids"] or not b["asks"] or sym not in self.e.markets:
                continue
            m = self.e.markets[sym]
            tick = 10 ** -m.price_decimals
            bid, ask = b["bids"][0][0], b["asks"][0][0]
            p = self.pos.get(a, {"qty": 0.0, "cost": 0.0})
            exit_now = self.stopped or self.must_exit(a, now)
            target = 0.0 if exit_now else self.capital * self.weights.get(a, 0.0) * self.scale * wind
            cur = p["qty"] * bid
            o = self.orders.get(a)
            if not self.market_open(a, now):
                continue
            if exit_now and p["qty"] > 0:
                if o:
                    self.cancel(a)
                self.sell_now(a, m, books, self.stopped or "scheduled exit (USDT market hours / challenge end)")
                continue
            deficit = target - cur
            min_step = max(m.min_notional, 60_000, 0.03 * target)
            if deficit > min_step and wind >= 1 and self.e.entries_allowed(now):
                self.trim_t0.pop(a, None)
                age = now - o["t"] if o else 0
                if o and o["side"] == "BUY" and age < self.cfg.get("maker_timeout_s", 300):
                    if o["price"] < bid - tick / 2:            # outbid: move up to the new best bid
                        self.cancel(a)
                    else:
                        continue
                elif o:
                    self.cancel(a)
                taker = bool(o) and age >= self.cfg.get("maker_timeout_s", 300)
                price = ask if taker else min(bid + tick, ask - tick) if ask - bid > tick else bid
                self.place(a, "BUY", deficit / price, price, taker,
                           f"{self.name}: build {a} toward {target:,.0f} TMN ({'taker after maker timeout' if taker else 'maker at the best bid'})",
                           now)
            elif deficit < -max(min_step, 0.15 * target) and not exit_now:
                # trim: maker ask at the top of the book, re-placed when undercut; during the end-of-challenge
                # wind-down a step not sold within wind_down_taker_after_s is sold as taker (schedule is kept)
                since = self.trim_t0.setdefault(a, now)
                taker = wind < 1 and now - since >= self.cfg.get("wind_down_taker_after_s", 900)
                if o and o["side"] == "SELL" and not taker and o["price"] <= ask + tick / 2:
                    continue                                   # our ask is still the best ask
                if o:
                    self.cancel(a)
                    p = self.pos.get(a, p)
                    deficit = target - p["qty"] * bid
                    if deficit >= -min_step:
                        continue
                why = (f"{self.name}: end-of-challenge wind-down, {wind*100:.0f}% of the sleeve still held"
                       if wind < 1 else f"{self.name}: trim {a} to target {target:,.0f} TMN (AI/regime lowered exposure)")
                if taker:
                    self.sell_now(a, m, books, why + f" (maker ask unfilled for {(now - since)/60:.0f} min -> taker)",
                                  qty=-deficit / bid)
                else:
                    self.place(a, "SELL", min(p["qty"], -deficit / bid), max(ask - tick, bid + tick), False, why, now)
            else:
                self.trim_t0.pop(a, None)

    def sell_now(self, a, m, books, why, qty=None):
        """Taker sale of `qty` (default: the whole position) at the live bids."""
        p = self.pos.get(a)
        if not p or p["qty"] <= 0:
            return
        free = self.e.bal().get(a, {}).get("free", 0.0)
        q = min(p["qty"], free, qty if qty is not None else p["qty"])
        b = books.get(f"{a}TMN", {}).get("bids") or [[0, 0]]
        if q * b[0][0] < m.min_notional:
            return
        f = self.e.ex.market_sell(m, q, books, self.e.fees.tmn_taker)
        self.e.dirty()
        if f.qty:
            part = p["cost"] * min(1.0, f.qty / p["qty"])
            self.realised += (f.quote - f.fee_quote) - part
            p["qty"] = max(0.0, p["qty"] - f.qty)
            p["cost"] -= part
            self.e.dlog.write("sleeve_exit", sleeve=self.name, asset=a, qty=f.qty, avg_price=f.avg_price, why=why)
