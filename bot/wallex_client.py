"""Thin, defensive REST client for the Wallex public + account API (v1).

Docs: https://api-docs.wallex.ir  /  https://developers.wallex.ir
Every call: retries with backoff, 429 handling, timeouts, and structured errors,
so the engine never crashes on a transient network problem.
"""
from __future__ import annotations

import time
import uuid
import logging
import threading
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_UP

import requests

log = logging.getLogger("wallex")

BASE_URL = "https://api.wallex.ir"


class WallexError(Exception):
    def __init__(self, msg, status=None, payload=None):
        super().__init__(msg)
        self.status = status
        self.payload = payload


@dataclass
class MarketInfo:
    symbol: str
    base: str
    quote: str
    qty_decimals: int
    price_decimals: int
    min_qty: float
    min_notional: float
    bid: float
    ask: float
    last: float
    quote_volume_24h: float

    @property
    def spread_pct(self) -> float:
        if self.bid <= 0 or self.ask <= 0:
            return 999.0
        return (self.ask - self.bid) / ((self.ask + self.bid) / 2) * 100

    def round_qty(self, q: float) -> float:
        step = Decimal(1).scaleb(-self.qty_decimals)
        return float(Decimal(str(q)).quantize(step, rounding=ROUND_DOWN))

    def round_price(self, p: float, side: str) -> float:
        step = Decimal(1).scaleb(-self.price_decimals)
        rnd = ROUND_DOWN if side == "BUY" else ROUND_UP  # never overpay / undersell by rounding
        return float(Decimal(str(p)).quantize(step, rounding=rnd))


def _fmt(x: float, decimals: int | None) -> str:
    """Plain decimal string for the API: never scientific notation (1e-05) and no spurious '.0' on
    integer-tick Toman prices."""
    if decimals is None:
        d = Decimal(repr(float(x))).normalize()
        return format(d, "f")
    return f"{x:.{max(0, int(decimals))}f}"


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


class _RateLimiter:
    def __init__(self, per_sec: float):
        self.min_interval = 1.0 / per_sec
        self.lock = threading.Lock()
        self.last = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            sleep = self.last + self.min_interval - now
            if sleep > 0:
                time.sleep(sleep)
            self.last = time.monotonic()


class WallexClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL,
                 timeout: float = 10.0, max_retries: int = 4, per_sec: float = 4.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json",
                                     "User-Agent": "wallex-ai-bot/1.0"})
        self.limiter = _RateLimiter(per_sec)
        self.stats = {"requests": 0, "errors": 0, "retries": 0, "rate_limited": 0}

    # ------------------------------------------------------------------ core
    def _request(self, method: str, path: str, *, params=None, json=None, auth=False):
        url = f"{self.base_url}{path}"
        headers = {}
        if auth:
            if not self.api_key:
                raise WallexError("API key required for " + path)
            headers["X-API-Key"] = self.api_key
        last_exc = None
        for attempt in range(self.max_retries + 1):
            self.limiter.wait()
            self.stats["requests"] += 1
            try:
                r = self.session.request(method, url, params=params, json=json,
                                         headers=headers, timeout=self.timeout)
            except requests.RequestException as e:
                last_exc = e
                self.stats["retries"] += 1
                time.sleep(min(8, 0.5 * 2 ** attempt))
                continue
            if r.status_code == 429:
                self.stats["rate_limited"] += 1
                time.sleep(min(15, 1.0 * 2 ** attempt))
                continue
            if r.status_code >= 500:
                self.stats["retries"] += 1
                time.sleep(min(8, 0.5 * 2 ** attempt))
                last_exc = WallexError(f"server {r.status_code}", r.status_code, r.text[:300])
                continue
            try:
                data = r.json()
            except ValueError:
                self.stats["errors"] += 1
                raise WallexError(f"non-JSON response {r.status_code}", r.status_code, r.text[:300])
            if r.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False):
                self.stats["errors"] += 1
                msg = data.get("message") if isinstance(data, dict) else str(data)
                raise WallexError(f"{method} {path} -> {r.status_code}: {msg}", r.status_code, data)
            return data
        self.stats["errors"] += 1
        raise WallexError(f"{method} {path} failed after retries: {last_exc}")

    # --------------------------------------------------------------- public
    def markets(self) -> dict[str, MarketInfo]:
        data = self._request("GET", "/v1/markets")
        out = {}
        for sym, m in data["result"]["symbols"].items():
            st = m.get("stats", {}) or {}
            out[sym] = MarketInfo(
                symbol=sym,
                base=m.get("baseAsset", ""),
                quote=m.get("quoteAsset", ""),
                qty_decimals=int(_f(m.get("stepSize"), 0)),
                price_decimals=int(_f(m.get("tickSize"), 0)),
                min_qty=_f(m.get("minQty")),
                min_notional=_f(m.get("minNotional")),
                bid=_f(st.get("bidPrice")),
                ask=_f(st.get("askPrice")),
                last=_f(st.get("lastPrice")),
                quote_volume_24h=_f(st.get("24h_quoteVolume")),
            )
        return out

    def depth(self, symbol: str) -> dict:
        data = self._request("GET", "/v1/depth", params={"symbol": symbol})
        res = data["result"]
        bids = [(_f(x["price"]), _f(x["quantity"])) for x in res.get("bid", [])]
        asks = [(_f(x["price"]), _f(x["quantity"])) for x in res.get("ask", [])]
        bids.sort(key=lambda t: -t[0])
        asks.sort(key=lambda t: t[0])
        return {"bids": bids, "asks": asks}

    def depth_all(self) -> dict[str, dict]:
        """All order books in ONE request (v2). Returns {symbol: {"bids": [(p,q)], "asks": [(p,q)]}}
        sorted best-first. This is what lets us price 9+ markets every ~2 seconds cheaply."""
        data = self._request("GET", "/v2/depth/all")
        out = {}
        for sym, book in (data.get("result") or {}).items():
            if not isinstance(book, dict):
                continue
            bids = sorted(((_f(x["price"]), _f(x["quantity"])) for x in book.get("bid", [])), key=lambda t: -t[0])
            asks = sorted(((_f(x["price"]), _f(x["quantity"])) for x in book.get("ask", [])), key=lambda t: t[0])
            out[sym] = {"bids": bids, "asks": asks}
        return out

    def prop_package(self, package_id: int) -> dict:
        """Trade-credit package details incl. the list of markets NOT allowed for it."""
        data = self._request("GET", f"/v1/prop/packages/{package_id}")
        return data["result"]

    def trades(self, symbol: str) -> list[dict]:
        data = self._request("GET", "/v1/trades", params={"symbol": symbol})
        return data["result"].get("latestTrades", [])

    def candles(self, symbol: str, resolution: str, frm: int, to: int) -> dict:
        """OHLCV via TradingView UDF endpoint. resolution in minutes ('5','60') or 'D'."""
        data = self._request("GET", "/v1/udf/history",
                             params={"symbol": symbol, "resolution": resolution,
                                     "from": int(frm), "to": int(to)})
        if data.get("s") != "ok":
            return {"t": [], "o": [], "h": [], "l": [], "c": [], "v": []}
        return {k: [_f(x) for x in data.get(k, [])] for k in ("t", "o", "h", "l", "c", "v")}

    # -------------------------------------------------------------- account
    def balances(self) -> dict[str, dict]:
        data = self._request("GET", "/v1/account/balances", auth=True)
        out = {}
        for asset, b in data["result"]["balances"].items():
            out[asset] = {"free": _f(b.get("value")) - _f(b.get("locked")),
                          "total": _f(b.get("value")), "locked": _f(b.get("locked"))}
        return out

    def fees(self) -> dict[str, dict]:
        data = self._request("GET", "/v1/account/fee", auth=True)
        res = data.get("result", {})
        if isinstance(res, list):  # docs show a list wrapping a map in some versions
            merged = {}
            for item in res:
                if isinstance(item, dict):
                    merged.update(item)
            res = merged
        return {s: {"maker": _f(v.get("makerFeeRate")), "taker": _f(v.get("takerFeeRate"))}
                for s, v in res.items() if isinstance(v, dict)}

    def place_order(self, symbol: str, side: str, qty: float, price: float,
                    order_type: str = "LIMIT", client_id: str | None = None,
                    qty_decimals: int | None = None, price_decimals: int | None = None) -> dict:
        client_id = client_id or f"AIB-{uuid.uuid4().hex[:20]}"
        body = {"symbol": symbol, "type": order_type, "side": side,
                "price": _fmt(price, price_decimals), "quantity": _fmt(qty, qty_decimals), "client_id": client_id}
        data = self._request("POST", "/v1/account/orders", json=body, auth=True)
        return data["result"]

    def get_order(self, client_order_id: str) -> dict:
        data = self._request("GET", f"/v1/account/orders/{client_order_id}", auth=True)
        return data["result"]

    def cancel_order(self, client_order_id: str) -> dict:
        data = self._request("DELETE", "/v1/account/orders",
                             params={"clientOrderId": client_order_id}, auth=True)
        return data.get("result", {})

    def open_orders(self, symbol: str | None = None) -> list[dict]:
        params = {"symbol": symbol} if symbol else None
        data = self._request("GET", "/v1/account/openOrders", params=params, auth=True)
        return data["result"].get("orders", [])

    def my_trades(self, symbol: str | None = None) -> list[dict]:
        params = {"symbol": symbol} if symbol else None
        data = self._request("GET", "/v1/account/trades", params=params, auth=True)
        return data["result"].get("AccountLatestTrades", [])


# ---------------------------------------------------------------- book helpers
def vwap_buy(asks, quote_amount: float):
    """Average price & base qty to spend `quote_amount` walking the asks (None if book too thin)."""
    rem, qty = quote_amount, 0.0
    for p, q in asks:
        take = min(rem, p * q)
        qty += take / p
        rem -= take
        if rem <= 1e-12:
            return quote_amount / qty, qty
    return None, None


def vwap_sell(bids, base_qty: float):
    """Average price & quote received selling `base_qty` into the bids (None if too thin)."""
    rem, got = base_qty, 0.0
    for p, q in bids:
        take = min(rem, q)
        got += take * p
        rem -= take
        if rem <= 1e-15:
            return got / base_qty, got
    return None, None
