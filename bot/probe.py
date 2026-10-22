"""Market probe: snapshot everything needed to (re)choose the strategy from inside Iran.

The Wallex API only resolves from Iranian networks, so research runs where the bot runs. The
supervisor starts `python run.py probe` on every deploy and syncs logs/probe/ to the
`runtime-logs` branch as soon as it finishes. Read-only: no order is ever placed here.

Output (logs/probe/):
  meta.json        time, package rules (raw), account fees, balances, open orders, own recent trades
  markets.json     every market: bid/ask/last/24h volume, tick/step, min notional, allowed flag
  depth_all.json   top 10 levels of every allowed order book (one /v2/depth/all call)
  trades.json      latest trade tape of the most active allowed markets
  candles_tmn.json / candles_usdt.json
                   1-minute OHLCV, last `days` days, for the most active allowed TMN markets
                   (+ USDTTMN) and their USDT pairs. Files are kept small (the logs are pushed
                   from Iran to GitHub, which is slow).
"""
from __future__ import annotations

import json
import logging
import os
import time

from .data import minute_bars
from .wallex_client import WallexClient, WallexError

log = logging.getLogger("probe")


def _dump(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, default=str)
    os.replace(tmp, path)


def _r(x):
    return float(f"{x:.7g}")


def run_probe(cfg: dict, api_key: str | None, out_dir: str = "logs/probe", days: float = 2, top: int = 20):
    os.makedirs(out_dir, exist_ok=True)
    c = WallexClient(api_key, per_sec=cfg["execution"].get("max_requests_per_sec", 5))
    meta = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "errors": {}}

    def safe(name, fn):
        try:
            return fn()
        except (WallexError, KeyError, TypeError, ValueError) as e:
            meta["errors"][name] = str(e)[:300]
            log.warning("probe %s failed: %s", name, e)
            return None

    pkg = safe("package", lambda: c._request("GET", f"/v1/prop/packages/{cfg['challenge']['package_id']}")["result"])
    meta["package"] = pkg
    unavailable = set((pkg or {}).get("unavailableMarkets") or [])
    if api_key:
        meta["fees"] = safe("fees", c.fees)
        meta["balances"] = safe("balances", c.balances)
        meta["open_orders"] = safe("open_orders", c.open_orders)
        meta["my_trades"] = safe("my_trades", c.my_trades)
    _dump(os.path.join(out_dir, "meta.json"), meta)

    mk = safe("markets", c.markets) or {}
    markets = {s: {**m.__dict__, "allowed": s not in unavailable} for s, m in mk.items()}
    _dump(os.path.join(out_dir, "markets.json"), markets)

    books = safe("depth_all", c.depth_all) or {}
    books = {s: {k: [[_r(p), _r(q)] for p, q in b[k][:10]] for k in ("bids", "asks")}
             for s, b in books.items() if markets.get(s, {}).get("allowed")}
    _dump(os.path.join(out_dir, "depth_all.json"), {"t": time.time(), "books": books})

    tmn = sorted((s for s, m in markets.items() if m["quote"] == "TMN" and m["allowed"] and s != "USDTTMN"),
                 key=lambda s: -markets[s]["quote_volume_24h"])[:top]
    usdt = [f"{s[:-3]}USDT" for s in tmn if f"{s[:-3]}USDT" in markets and markets[f"{s[:-3]}USDT"]["allowed"]]
    syms = ["USDTTMN"] + tmn + usdt
    meta["selected_symbols"] = syms
    trades = {}
    for s in syms:
        trades[s] = safe(f"trades {s}", lambda s=s: c.trades(s))
    _dump(os.path.join(out_dir, "trades.json"), trades)

    for name, group in (("candles_tmn.json", ["USDTTMN"] + tmn), ("candles_usdt.json", usdt)):
        candles = {}
        for s in group:
            df = safe(f"candles {s}", lambda s=s: minute_bars(c, s, days))
            if df is not None and len(df):
                candles[s] = {"t": df.index.tolist(),
                              **{k: [_r(x) for x in df[k].astype(float)] for k in "ohlcv" if k in df}}
        _dump(os.path.join(out_dir, name), candles)

    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    meta["requests"] = c.stats
    _dump(os.path.join(out_dir, "meta.json"), meta)
    return meta
