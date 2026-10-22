"""Founder view: the real Wallex account and the real bot running on Liara, read-only.

Wallex account : WALLEX_API_KEY (same key as the bot; only balances / open orders / trades are read, a few
                 requests a minute next to the bot's ~5/s). Equity is valued like the engine does it:
                 every asset at the best Toman bid (via USDT for coins without a Toman book).
Bot            : first source available, merged:
                 BOT_LOGS_DIR   the bot's logs/ folder (same server) - complete and real-time
                 BOT_STATUS_URL the bot app's existing status page on Liara - real-time, last 60 events
                 GITHUB_TOKEN   the runtime-logs branch the bot pushes every 10 min - full history
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import threading
import time

import requests

from .settings import ROOT, settings

log = logging.getLogger("portal.telemetry")

SKIP_EVENTS = {"quote", "buy_unblocked", "quote_unblocked", "coin_skipped", "state_restored"}
SLEEVE_FA = {"rial": "سبد ریال", "beta": "سبد بتا"}
SIDE_FA = {"BUY": "خرید", "SELL": "فروش"}


def _n(x, d=0) -> str:
    try:
        return f"{float(x):,.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def render_event(e: dict) -> dict | None:
    """Decision-log record -> {ts, time, kind, text (Persian), detail}. None = not worth showing."""
    ev = e.get("event", "")
    if ev in SKIP_EVENTS or (ev == "usdt_ref_check" and not e.get("problem")):
        return None
    kind, detail = "info", ""
    if ev == "policy":
        p = e.get("policy") or {}
        mk = "، ".join(f"{k} (h={v}٪)" for k, v in (p.get("markets") or {}).items()) or "هیچ بازاری"
        sl = p.get("sleeves") or {}
        text = (f"تصمیم AI ({p.get('source', '?')}): بازارسازی در {mk}؛ حضور سبد ریال {sl.get('rial', '-')} و "
                f"سبد بتا {sl.get('beta', '-')}؛ کوین‌های بتا: {', '.join(p.get('beta_assets') or []) or '-'}"
                + ("؛ توقف کامل" if p.get("pause") else ""))
        kind, detail = "ai", p.get("reasoning", "")
    elif ev == "regime":
        text = (f"رژیم تتر/تومان {_n(e.get('usdt_tmn'))}: ۶ ساعت {e.get('ch6_pct')}٪، ۲۴ ساعت {e.get('ch24_pct')}٪، "
                f"۴۸ ساعت {e.get('ch48_pct')}٪ ← سقف حضور سبدها {e.get('cap')}")
        kind = "regime"
    elif ev == "fill":
        pnl = e.get("pnl_tmn")
        text = (f"بازارساز: {SIDE_FA.get(e.get('side'), e.get('side'))} {e.get('coin')} به ارزش {_n(e.get('notional_tmn'))} "
                f"تومان" + (f"، سود/زیان {_n(pnl)} تومان" if pnl not in (None, 0) else ""))
        kind, detail = "trade", e.get("why", "")
    elif ev == "exit":
        text = f"خروج بازارساز از {e.get('coin')}: سود/زیان {_n(e.get('pnl_tmn'))} تومان"
        kind, detail = "risk", e.get("why", "")
    elif ev == "sleeve_order":
        text = (f"سفارش {SLEEVE_FA.get(e.get('sleeve'), e.get('sleeve'))}: {SIDE_FA.get(e.get('side'), '')} "
                f"{e.get('asset')} {_n(e.get('size_tmn'))} تومان ({'Taker' if e.get('taker') else 'Maker'})")
        kind, detail = "order", e.get("why", "")
    elif ev == "sleeve_fill":
        text = (f"پر شد — {SLEEVE_FA.get(e.get('sleeve'), e.get('sleeve'))}: {SIDE_FA.get(e.get('side'), '')} "
                f"{e.get('asset')} به ارزش {_n(e.get('notional_tmn'))} تومان")
        kind, detail = "trade", e.get("why", "")
    elif ev in ("sleeve_stop", "sleeve_exit"):
        text = f"{SLEEVE_FA.get(e.get('sleeve'), e.get('sleeve'))}: {e.get('why', '')}"
        kind = "risk"
    elif ev == "sleeve_reweight":
        text = "AI کوین‌های سبد بتا را عوض کرد: " + "، ".join(f"{k} {v}" for k, v in (e.get("weights") or {}).items())
        kind = "ai"
    elif ev in ("circuit_breaker_pause", "kill_switch"):
        text = ("Circuit breaker: افت از اوج؛ همه‌چیز به تومان و مکث" if ev == "circuit_breaker_pause"
                else "توقف دائمی ربات (kill switch)")
        kind, detail = "risk", e.get("reason", "")
    elif ev == "flatten":
        text = f"تبدیل همه‌چیز به تومان ({e.get('reason')})، ارزش {_n(e.get('equity'))} تومان"
        kind = "risk"
    elif ev in ("buy_blocked", "quote_blocked"):
        text = f"محافظ: خرید {e.get('coin')} موقتاً متوقف شد"
        kind, detail = "guard", e.get("why", "")
    elif ev == "startup":
        text = "ربات (دوباره) شروع به کار کرد"
    elif ev == "error":
        text = "خطا در یک چرخه (ربات ادامه می‌دهد)"
        kind, detail = "error", e.get("error", "")
    elif ev == "live_self_test":
        text = "تست مسیر سفارش واقعی: " + ("موفق" if e.get("ok") else "ناموفق — معامله‌ی واقعی شروع نشد")
        kind = "risk" if not e.get("ok") else "info"
    elif ev == "wind_down_step":
        text = f"خروج پله‌ای پایان مسابقه: {e.get('share_still_held')} از سبدها هنوز نگه داشته می‌شود"
    elif ev == "state_reset":
        text = "تست سایه از سرمایه‌ی اولیه دوباره شروع شد (تنظیمات پرتفوی عوض شده بود)"
    elif ev == "instance_superseded":
        text = "نسخه‌ی جدیدتر ربات جایگزین این نسخه شد (استقرار جدید)"
    else:
        text = ev.replace("_", " ")
        detail = e.get("why", "") or e.get("reason", "")
    return {"ts": e.get("ts"), "time": e.get("time", ""), "event": ev, "kind": kind, "text": text,
            "detail": str(detail)[:1200]}


def parse_equity_csv(text: str) -> list[dict]:
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        try:
            rows.append({"ts": float(r["ts"]), "equity": float(r["equity"]), "drawdown_pct": float(r.get("drawdown_pct") or 0),
                         "fills": int(float(r.get("fills") or 0)), "pnl_tmn": float(r.get("pnl_tmn") or 0),
                         "volume_tmn": float(r.get("volume_tmn") or 0), "coins_tmn": float(r.get("coins_tmn") or 0)})
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def parse_sleeves_csv(text: str) -> dict | None:
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return None
    last, out = rows[-1], {}
    for name in ("rial", "beta"):
        try:
            out[name] = {"value": float(last[f"{name}_value"]), "pnl": float(last[f"{name}_pnl"]),
                         "ret_pct": float(last[f"{name}_ret_pct"]), "scale": float(last[f"{name}_scale"])}
        except (KeyError, TypeError, ValueError):
            pass
    out["ts"] = float(last.get("ts") or 0)
    return out


def downsample(rows: list, n=400) -> list:
    if len(rows) <= n:
        return rows
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)] + [rows[-1]]


def _tail(path: str, max_bytes: int) -> str:
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        data = f.read().decode("utf-8", errors="replace")
    return data if size <= max_bytes else data.split("\n", 1)[-1]


class BotTelemetry:
    def __init__(self):
        self.lock = threading.Lock()
        self.data: dict = {}
        self.last_github = 0.0
        self.github: dict = {}
        self.remember: dict = {}          # last policy / regime ever seen (they are rare in the event stream)

    # ------------------------------------------------------------------ sources
    def _mode_local(self, d: str) -> str:
        if settings.bot_mode_hint:
            return settings.bot_mode_hint
        try:
            return open(os.path.join(os.path.dirname(d.rstrip("/")), "control", "mode.txt")).read().strip()
        except OSError:
            pass
        files = [(os.path.getmtime(os.path.join(d, f"equity_{m}.csv")), m) for m in ("live", "shadow")
                 if os.path.exists(os.path.join(d, f"equity_{m}.csv"))]
        return max(files)[1] if files else "shadow"

    def from_local(self) -> dict:
        d = settings.bot_logs_dir
        mode = self._mode_local(d)
        out = {"source": "logs_dir", "mode": mode}
        p = os.path.join(d, f"equity_{mode}.csv")
        if os.path.exists(p):
            out["equity_rows"] = parse_equity_csv(open(p, encoding="utf-8").read())
        p = os.path.join(d, f"sleeves_{mode}.csv")
        if os.path.exists(p):
            out["sleeves"] = parse_sleeves_csv(open(p, encoding="utf-8").read())
        p = os.path.join(d, f"decisions_{mode}.jsonl")
        if os.path.exists(p):
            out["records"] = [json.loads(x) for x in _tail(p, 600_000).splitlines() if x.strip().startswith("{")]
        p = os.path.join(d, f"bot_{mode}.out")
        if os.path.exists(p):
            out["console"] = _tail(p, 20_000).splitlines()[-60:]
        return out

    def from_status_url(self) -> dict:
        base = settings.bot_status_url
        out = {"source": "status_url"}
        home = requests.get(base + "/", timeout=8).text
        lines = home.splitlines()
        out["mode"] = lines[0].split(":", 1)[1].strip() if lines and lines[0].startswith("mode:") else "?"
        csv_lines = [x for x in lines if x.count(",") >= 8 and x.split(",")[0].isdigit()]
        header = "ts,time,equity,drawdown_pct,fills,pnl_tmn,volume_tmn,usdt_tmn,coins_tmn\n"
        out["equity_rows"] = parse_equity_csv(header + "\n".join(csv_lines))
        try:
            dec = requests.get(base + "/decisions", timeout=10).text
            out["records"] = [json.loads(b) for b in dec.split("\n\n") if b.strip().startswith("{")]
        except (requests.RequestException, ValueError):
            pass
        try:
            out["console"] = requests.get(base + "/bot", timeout=8).text.splitlines()[-60:]
        except requests.RequestException:
            pass
        return out

    def _gh(self, path: str) -> str | None:
        r = requests.get(f"https://api.github.com/repos/{settings.github_repo}/contents/{path}",
                         params={"ref": "runtime-logs"}, timeout=30,
                         headers={"Authorization": f"Bearer {settings.github_token}",
                                  "Accept": "application/vnd.github.raw+json"})
        return r.text if r.ok else None

    def from_github(self, mode: str) -> dict:
        out = {"source": "github"}
        t = self._gh(f"logs/equity_{mode}.csv")
        if t:
            out["equity_rows"] = parse_equity_csv(t)
        t = self._gh(f"logs/sleeves_{mode}.csv")
        if t:
            out["sleeves"] = parse_sleeves_csv(t)
        t = self._gh(f"logs/decisions_{mode}.jsonl")
        if t:
            out["records"] = [json.loads(x) for x in t.splitlines()[-4000:] if x.strip().startswith("{")]
        return out

    # ------------------------------------------------------------------ merge
    def refresh(self) -> dict:
        parts, errors = [], []
        if settings.bot_logs_dir and os.path.isdir(settings.bot_logs_dir):
            try:
                parts.append(self.from_local())
            except Exception as e:                       # noqa: BLE001
                errors.append(f"logs_dir: {e}")
        if not parts and settings.bot_status_url:
            try:
                parts.append(self.from_status_url())
            except Exception as e:                       # noqa: BLE001
                errors.append(f"status_url: {e}")
        mode = next((p["mode"] for p in parts if p.get("mode") not in (None, "?")), settings.bot_mode_hint or "shadow")
        if settings.github_token and not any(p["source"] == "logs_dir" for p in parts):
            if time.time() - self.last_github > 300:
                self.last_github = time.time()
                try:
                    self.github = self.from_github(mode)
                except Exception as e:                   # noqa: BLE001
                    errors.append(f"github: {e}")
            if self.github:
                parts.append(self.github)
        if not parts:
            with self.lock:
                if self.data.get("ok") or self.data.get("stale"):       # keep the last good picture, flagged
                    self.data = {**self.data, "ok": False, "stale": True, "errors": errors}
                else:
                    self.data = {"configured": bool(settings.bot_logs_dir or settings.bot_status_url
                                                    or settings.github_token), "ok": False, "errors": errors,
                                 "ts": time.time()}
            return self.data

        rows: dict[float, dict] = {}
        records: dict[tuple, dict] = {}
        for p in reversed(parts):                        # later = more real-time source wins
            for r in p.get("equity_rows", []):
                rows[r["ts"]] = r
            for r in p.get("records", []):
                records[(r.get("ts"), r.get("event"))] = r
        rows_l = sorted(rows.values(), key=lambda r: r["ts"])
        recs = sorted(records.values(), key=lambda r: r.get("ts") or 0)
        for r in recs:
            if r.get("event") in ("policy", "regime"):
                self.remember[r["event"]] = r
        events = [x for x in (render_event(r) for r in recs[-400:]) if x][-120:][::-1]
        last = rows_l[-1] if rows_l else {}
        init = float(settings.engine_config["challenge"]["initial_capital_tmn"])
        sleeves = next((p["sleeves"] for p in parts if p.get("sleeves")), None)
        policy = self.remember.get("policy")
        data = {
            "configured": True, "ok": True, "errors": errors, "ts": time.time(),
            "sources": [p["source"] for p in parts], "mode": mode,
            "updated_ts": last.get("ts"), "age_s": round(time.time() - last["ts"]) if last else None,
            "equity": last.get("equity"), "initial": init,
            "pnl_tmn": (last["equity"] - init) if last else None,
            "pnl_pct": round((last["equity"] / init - 1) * 100, 3) if last else None,
            "drawdown_pct": last.get("drawdown_pct"), "max_drawdown_pct": max((r["drawdown_pct"] for r in rows_l), default=None),
            "mm": {"fills": last.get("fills"), "pnl_tmn": last.get("pnl_tmn"), "volume_tmn": last.get("volume_tmn"),
                   "inventory_tmn": last.get("coins_tmn")},
            "history": [[r["ts"], r["equity"]] for r in downsample(rows_l)],
            "sleeves": sleeves,
            "policy": (policy or {}).get("policy"), "policy_time": (policy or {}).get("time"),
            "regime": self.remember.get("regime"),
            "events": events,
            "guards_last_hour": sum(1 for r in recs if r.get("event") in ("buy_blocked", "quote_blocked")
                                    and (r.get("ts") or 0) > time.time() - 3600),
            "console": next((p["console"] for p in parts if p.get("console")), []),
        }
        with self.lock:
            self.data = data
        return data

    def get(self) -> dict:
        with self.lock:
            return dict(self.data)


class WallexAccount:
    """The founder's real Wallex account, valued in Toman at the best bids."""

    def __init__(self):
        self.lock = threading.Lock()
        self.data: dict = {}
        self.client = None
        self.last_trades = 0.0
        self.trades: list = []

    def _client(self):
        if self.client is None:
            import sys
            sys.path.insert(0, ROOT)
            from bot.wallex_client import WallexClient
            self.client = WallexClient(settings.wallex_api_key, per_sec=1, max_retries=1)
        return self.client

    @staticmethod
    def sleeve_of(asset: str) -> str:
        pf = (settings.engine_config.get("portfolio") or {}).get("sleeves") or {}
        if asset == "TMN":
            return "cash"
        if asset in (pf.get("rial") or {}).get("assets", {}):
            return "medium"
        beta = pf.get("beta") or {}
        if asset in beta.get("assets", {}) or asset in beta.get("universe", []):
            return "high"
        if asset == "USDT":
            return "other"
        return "low"

    def refresh(self) -> dict:
        if not settings.wallex_api_key:
            with self.lock:
                self.data = {"configured": False, "ok": False}
            return self.data
        c = self._client()
        try:
            bal = c.balances()
            books = c.depth_all()
            usdt_bid = (books.get("USDTTMN", {}).get("bids") or [[0]])[0][0]
            holdings, by_sleeve, eq = [], {"cash": 0.0, "low": 0.0, "medium": 0.0, "high": 0.0, "other": 0.0}, 0.0
            for a, x in bal.items():
                q = x.get("total", 0.0)
                if q <= 0:
                    continue
                if a == "TMN":
                    px = 1.0
                else:
                    tb = books.get(f"{a}TMN", {}).get("bids")
                    ub = books.get(f"{a}USDT", {}).get("bids")
                    px = tb[0][0] if tb else (ub[0][0] * usdt_bid if ub else 0.0)
                v = q * px
                if a != "TMN" and v < 1000:               # dust
                    continue
                s = self.sleeve_of(a)
                by_sleeve[s] += v
                eq += v
                holdings.append({"asset": a, "qty": q, "locked": x.get("locked", 0.0), "price": px, "value_tmn": v, "sleeve": s})
            oo = c.open_orders()
            if time.time() - self.last_trades > 60:
                self.last_trades = time.time()
                try:
                    self.trades = c.my_trades()[:30]
                except Exception as e:                    # noqa: BLE001
                    log.info("my_trades: %s", e)
            init = float(settings.engine_config["challenge"]["initial_capital_tmn"])
            data = {"configured": True, "ok": True, "ts": time.time(), "equity_tmn": eq, "initial_tmn": init,
                    "pnl_tmn": eq - init, "pnl_pct": round((eq / init - 1) * 100, 3) if init else None,
                    "holdings": sorted(holdings, key=lambda h: -h["value_tmn"]), "by_sleeve": by_sleeve,
                    "open_orders": len(oo),
                    "open_orders_list": [{k: o.get(k) for k in ("symbol", "side", "price", "origQty", "executedQty",
                                                                 "status", "created_at") if k in o} for o in oo[:15]],
                    "recent_trades": self.trades}
        except Exception as e:                            # noqa: BLE001
            data = dict(self.data)
            data.update({"configured": True, "ok": False, "error": str(e)[:300], "error_ts": time.time()})
        with self.lock:
            self.data = data
        return data

    def get(self) -> dict:
        with self.lock:
            return dict(self.data)


bot_telemetry = BotTelemetry()
wallex_account = WallexAccount()
