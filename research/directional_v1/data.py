"""Market data helpers: chunked historical candle download + local CSV cache."""
from __future__ import annotations

import os
import time
import logging

import pandas as pd

from .features import candles_to_df
from .wallex_client import WallexClient, WallexError

log = logging.getLogger("data")


def fetch_history(client: WallexClient, symbol: str, resolution_min: int, days: float,
                  cache_dir: str = "data", chunk_hours: int = 48) -> pd.DataFrame:
    """Download `days` of candles in chunks (the UDF endpoint caps rows per call),
    merge with any cached file, save, and return a clean DataFrame."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{symbol}_{resolution_min}m.csv")
    cached = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    end = int(time.time())
    start = end - int(days * 86400)
    if not cached.empty:
        start = max(start, int(cached["t"].max()) - resolution_min * 60 * 3)
    parts = [cached] if not cached.empty else []
    t = start
    while t < end:
        t2 = min(end, t + chunk_hours * 3600)
        try:
            c = client.candles(symbol, str(resolution_min), t, t2)
            parts.append(candles_to_df(c))
        except WallexError as e:
            log.warning("candles %s %s-%s failed: %s", symbol, t, t2, e)
        t = t2
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    df = candles_to_df({k: df[k].tolist() for k in ("t", "o", "h", "l", "c", "v")}) if not df.empty else df
    df = df[df["t"] >= end - int(max(days, 30) * 86400)]
    df.to_csv(path, index=False)
    return df


def drop_open_bar(df: pd.DataFrame, resolution_min: int, now: float | None = None) -> pd.DataFrame:
    """Remove the still-forming last candle so signals use closed bars only."""
    now = now or time.time()
    if df.empty:
        return df
    if df["t"].iloc[-1] + resolution_min * 60 > now:
        return df.iloc[:-1]
    return df
