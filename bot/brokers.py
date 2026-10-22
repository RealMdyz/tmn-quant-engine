"""Execution layer — one interface, two implementations.

LiveExec : real orders on Wallex (challenge account)
PaperExec: shadow test — real live order books, simulated fills, no orders sent.

Paper fill model is conservative: a resting BUY fills when (a) the opposite side
of the live book (best ask) moves to/through our price, for the quantity offered
there, or (b) the real trade tape prints a trade strictly BELOW our price (a seller
swept the book through our level), for that trade's quantity. Marketable sells
fill against the live bids (VWAP) with taker fees.
"""
from __future__ import annotations

import time
import uuid
import logging
from dataclasses import dataclass, field

from .wallex_client import WallexClient, WallexError, MarketInfo, vwap_sell

log = logging.getLogger("exec")


@dataclass
class Fill:
    side: str
    symbol: str
    qty: float = 0.0          # base qty executed (gross)
    quote: float = 0.0        # quote amount executed (gross)
    fee_quote: float = 0.0
    orders: list = field(default_factory=list)
    note: str = ""

    @property
    def avg_price(self):
        return self.quote / self.qty if self.qty else 0.0


def _trade_ts(t: dict) -> float | None:
    """Epoch seconds of a /v1/trades row (ISO string or epoch s/ms); None if unparseable."""
    v = t.get("timestamp") or t.get("time")
    if v is None:
        return None
    try:
        x = float(v)
        return x / 1000 if x > 1e11 else x
    except (TypeError, ValueError):
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _cid(prefix="Q"):
    return f"{prefix}-{uuid.uuid4().hex[:22]}"


class LiveExec:
    def __init__(self, client: WallexClient, fees_by_symbol: dict):
        self.c = client
        self.fees = fees_by_symbol

    def balances(self):
        return self.c.balances()

    def place_limit(self, m: MarketInfo, side: str, qty: float, price: float, prefix="Q", taker=False) -> dict:
        qty, price = m.round_qty(qty), m.round_price(price, side)
        cid = _cid(prefix)
        o = self.c.place_order(m.symbol, side, qty, price, "LIMIT", client_id=cid,
                               qty_decimals=m.qty_decimals, price_decimals=m.price_decimals)
        o.setdefault("clientOrderId", cid)
        return o

    def cancel(self, cid: str):
        try:
            self.c.cancel_order(cid)
        except WallexError as e:
            log.info("cancel %s: %s", cid, e)

    def get(self, cid: str) -> dict:
        return self.c.get_order(cid)

    def open_orders(self) -> dict[str, dict]:
        return {o.get("clientOrderId"): o for o in self.c.open_orders()}

    def on_books(self, books):  # live fills happen on the exchange
        return None

    def market_sell(self, m: MarketInfo, qty: float, books: dict, fee: float, attempts: int = 2) -> Fill:
        """Fast hedge: marketable limit SELL priced at the level that covers the WHOLE quantity in the
        visible book, minus a safety buffer. The matching engine fills at the resting bids' prices
        (price improvement), so the aggressive limit costs nothing extra but fills at once.
        Status is polled every 0.3 s; the main loop is blocked ~1-3 s instead of up to ~17 s."""
        fill = Fill("SELL", m.symbol)
        remaining = m.round_qty(qty)
        for k in range(attempts):
            if remaining <= 0 or remaining < m.min_qty:
                break
            b = books.get(m.symbol) if k == 0 else self.c.depth(m.symbol)
            bids = b["bids"] if b else []
            if not bids:
                time.sleep(0.5)
                continue
            acc, level = 0.0, bids[-1][0]
            for p, q in bids:
                acc += q
                if acc >= remaining:
                    level = p
                    break
            px = level * (1 - 0.004 * (k + 1))
            if remaining * bids[0][0] < m.min_notional:
                fill.note = "below min notional"
                break
            try:
                o = self.place_limit(m, "SELL", remaining, px, prefix="H")
            except WallexError as e:
                fill.note = f"place failed: {e}"
                time.sleep(0.5)
                continue
            cid = o.get("clientOrderId")
            for _ in range(10):
                if not o.get("active", True) or float(o.get("executedPercent", 0) or 0) >= 100:
                    break
                time.sleep(0.3)
                try:
                    o = self.get(cid)
                except WallexError:
                    continue
            if o.get("active", True):
                self.cancel(cid)
                time.sleep(0.3)
                try:
                    o = self.get(cid)
                except WallexError:
                    pass
            q, s_ = float(o.get("executedQty", 0) or 0), float(o.get("executedSum", 0) or 0)
            fill.orders.append({"cid": cid, "status": o.get("status"), "qty": q, "sum": s_, "limit": px})
            if q > 0:
                fill.qty += q
                fill.quote += s_
                fill.fee_quote += s_ * fee
                remaining = m.round_qty(remaining - q)
        return fill


class PaperExec:
    def __init__(self, start: dict, fees_by_symbol: dict, default_fee: dict):
        self.bal = {k: {"free": v, "total": v, "locked": 0.0} for k, v in start.items()}
        self.orders: dict[str, dict] = {}
        self.fees = fees_by_symbol
        self.default_fee = default_fee
        self.markets: dict[str, MarketInfo] = {}

    def _fee(self, sym, kind):
        return self.fees.get(sym, {}).get(kind) or self.default_fee[("tmn_" if sym.endswith("TMN") else "usdt_") + kind]

    def _add(self, asset, free=0.0, locked=0.0):
        b = self.bal.setdefault(asset, {"free": 0.0, "total": 0.0, "locked": 0.0})
        b["free"] += free
        b["locked"] += locked
        b["total"] = b["free"] + b["locked"]

    def balances(self):
        return {k: dict(v) for k, v in self.bal.items()}

    def place_limit(self, m: MarketInfo, side: str, qty: float, price: float, prefix="Q", taker=False) -> dict:
        qty, price = m.round_qty(qty), m.round_price(price, side)
        self.markets[m.symbol] = m
        cid = _cid(prefix)
        if side == "BUY":
            cost = qty * price
            if cost > self.bal.get(m.quote, {}).get("free", 0) + 1e-9:
                raise WallexError("paper: insufficient balance")
            self._add(m.quote, -cost, cost)
        else:
            if qty > self.bal.get(m.base, {}).get("free", 0) + 1e-12:
                raise WallexError("paper: insufficient base balance")
            self._add(m.base, -qty, qty)
        o = {"clientOrderId": cid, "symbol": m.symbol, "side": side, "price": price, "origQty": qty,
             "executedQty": 0.0, "executedSum": 0.0, "active": True, "status": "NEW", "created": time.time(),
             "taker": taker}
        self.orders[cid] = o
        return dict(o)

    def cancel(self, cid):
        o = self.orders.get(cid)
        if not o or not o["active"]:
            return
        m = self.markets[o["symbol"]]
        rem = o["origQty"] - o["executedQty"]
        if o["side"] == "BUY":
            amt = rem * o["price"]
            self._add(m.quote, amt, -amt)
        else:
            self._add(m.base, rem, -rem)
        o["active"], o["status"] = False, "CANCELED"

    def get(self, cid):
        return dict(self.orders[cid])

    def open_orders(self):
        return {k: dict(v) for k, v in self.orders.items() if v["active"]}

    def on_books(self, books: dict):
        """Simulate maker fills: BUY fills when the live best ask <= our price."""
        for o in self.orders.values():
            if not o["active"]:
                continue
            b = books.get(o["symbol"])
            if not b:
                continue
            rem = o["origQty"] - o["executedQty"]
            if o["side"] == "BUY":
                avail = sum(q for p, q in b["asks"] if p <= o["price"])
            else:
                avail = sum(q for p, q in b["bids"] if p >= o["price"])
            self._fill(o, min(rem, avail))

    def on_trades(self, symbol: str, trades: list[dict], seen: set):
        """Simulate maker fills from the market's real trade tape. Our bid is not in the real book, so a
        seller who sweeps the book down to our price leaves no resting ask behind (on_books cannot see
        it) — but the sweep prints trades. Any NEW trade strictly below our bid price means our (higher)
        bid would have been hit first in reality; it fills us for at most that trade's quantity. Resting
        SELL orders mirror this: a new trade strictly above our ask fills us.
        `seen` holds trade keys already processed for this symbol (the first poll is only a baseline)."""
        fresh = []
        for t in trades:
            key = (t.get("timestamp") or t.get("time"), str(t.get("price")), str(t.get("quantity")))
            if key not in seen:
                seen.add(key)
                fresh.append(t)
        for o in self.orders.values():
            if not o["active"] or o["symbol"] != symbol:
                continue
            for t in fresh:
                try:
                    p, q = float(t["price"]), float(t["quantity"])
                except (KeyError, TypeError, ValueError):
                    continue
                ts = _trade_ts(t)
                if ts is not None and ts < o["created"] - 1:
                    continue                    # printed before our order existed
                rem = o["origQty"] - o["executedQty"]
                if rem <= 0 or not o["active"]:
                    break
                through = p < o["price"] * (1 - 1e-9) if o["side"] == "BUY" else p > o["price"] * (1 + 1e-9)
                if through:
                    self._fill(o, min(rem, q))
                    o["fill_source"] = "trade_tape"

    def _fill(self, o: dict, qty: float):
        m = self.markets[o["symbol"]]
        q = m.round_qty(qty)
        if q <= 0:
            return
        fee = self._fee(o["symbol"], "taker" if o.get("taker") else "maker")
        amt = q * o["price"]
        if o["side"] == "BUY":
            self._add(m.quote, 0, -amt)
            self._add(m.base, q * (1 - fee))
        else:
            self._add(m.base, 0, -q)
            self._add(m.quote, amt * (1 - fee))
        o["executedQty"] += q
        o["executedSum"] += amt
        if o["origQty"] - o["executedQty"] <= 10 ** -m.qty_decimals / 2:
            o["active"], o["status"] = False, "FILLED"
        else:
            o["status"] = "PARTIALLY_FILLED"

    def market_sell(self, m: MarketInfo, qty: float, books: dict, fee: float, attempts: int = 3) -> Fill:
        self.markets[m.symbol] = m
        b = books.get(m.symbol)
        qty = m.round_qty(min(qty, self.bal.get(m.base, {}).get("free", 0)))
        if not b or not b["bids"] or qty <= 0:
            return Fill("SELL", m.symbol, note="nothing to sell / empty book")
        px, got = vwap_sell(b["bids"], qty)
        if px is None or got < m.min_notional:
            return Fill("SELL", m.symbol, note="book too thin or below min notional")
        self._add(m.base, -qty)
        self._add(m.quote, got * (1 - fee))
        return Fill("SELL", m.symbol, qty=qty, quote=got, fee_quote=got * fee, note="paper taker")
