"""Historical candles from Wallex for backtesting.

Wallex UDF quirk (measured 2026-10-22): resolution=1 only serves ~1 day,
resolution=15 actually returns 1-MINUTE bars for up to ~10 days, and
resolution=60 serves ~29 days of hourly bars. We pull 1-minute bars via the
`15` resolution and aggregate to 5 minutes locally.
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from .wallex_client import WallexClient


def minute_bars(client: WallexClient, symbol: str, days: float = 10) -> pd.DataFrame:
    now = int(time.time()) // 60 * 60
    c = client.candles(symbol, "15", now - int(days * 86400), now)
    df = pd.DataFrame(c)
    if df.empty:
        return df
    df["t"] = df["t"].astype("int64")
    return df.drop_duplicates("t").sort_values("t").set_index("t")


def to_5min(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    idx = pd.to_datetime(df.index, unit="s")
    g = df.set_index(idx).resample("5min")
    out = pd.DataFrame({"o": g["o"].first(), "h": g["h"].max(), "l": g["l"].min(),
                        "c": g["c"].last(), "v": g["v"].sum()})
    out["c"] = out["c"].ffill()
    for k in ("o", "h", "l"):
        out[k] = out[k].fillna(out["c"])
    out = out.dropna()
    out.index = (out.index.astype("int64") // 10**9).astype("int64")
    return out


def load_or_fetch(client: WallexClient | None, symbols: list[str], cache: str = "data/m5_all.json",
                  days: float = 10) -> dict[str, pd.DataFrame]:
    """Returns {symbol: 5-min OHLCV frame}. Uses the cached research file when present."""
    if os.path.exists(cache) and client is None:
        raw = json.load(open(cache))
        return {s: pd.DataFrame({k: raw[s][k] for k in "ohlcv"}, index=np.array(raw[s]["t"], dtype="int64"))
                for s in symbols if s in raw}
    out = {}
    for s in symbols:
        out[s] = to_5min(minute_bars(client, s, days))
    os.makedirs(os.path.dirname(cache) or ".", exist_ok=True)
    json.dump({s: {"t": df.index.tolist(), **{k: df[k].tolist() for k in "ohlcv"}} for s, df in out.items()},
              open(cache, "w"))
    return out
