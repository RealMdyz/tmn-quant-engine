"""All portal settings come from environment variables (Liara: app settings -> environment variables)."""
from __future__ import annotations

import logging
import os
import secrets

import yaml

log = logging.getLogger("portal")

PORTAL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(PORTAL_DIR)          # repo root: bot/, config.yaml, data/


def _env(name, default=""):
    return os.getenv(name, default).strip()


class Settings:
    def __init__(self):
        self.data_dir = _env("PORTAL_DATA_DIR", os.path.join(PORTAL_DIR, "var"))
        os.makedirs(self.data_dir, exist_ok=True)
        self.database_url = _env("DATABASE_URL", f"sqlite:///{os.path.join(self.data_dir, 'portal.db')}")
        self.secret = _env("PORTAL_SECRET")
        if not self.secret:
            self.secret = secrets.token_hex(32)
            log.warning("PORTAL_SECRET is not set: sessions will not survive a restart")
        self.public_url = _env("PUBLIC_URL", "http://localhost:8000").rstrip("/")
        self.cookie_secure = _env("COOKIE_SECURE", "1" if self.public_url.startswith("https") else "0") == "1"
        self.session_days = int(_env("SESSION_DAYS", "14"))

        # founder account (created / updated at start-up)
        self.founder_email = _env("FOUNDER_EMAIL").lower()
        self.founder_password = _env("FOUNDER_PASSWORD")
        self.founder_name = _env("FOUNDER_NAME", "بنیان‌گذار")

        # real bot + real Wallex account of the founder (read-only use)
        self.wallex_api_key = _env("WALLEX_API_KEY")
        self.bot_status_url = _env("BOT_STATUS_URL").rstrip("/")
        self.bot_logs_dir = _env("BOT_LOGS_DIR")
        self.github_token = _env("GITHUB_TOKEN")
        self.github_repo = _env("GITHUB_REPO", "RealMdyz/tmn-quant-engine")
        self.bot_mode_hint = _env("BOT_MODE", "")        # shadow | live; empty = read it from the bot

        # market data for the users' bots: wallex (live public API) | replay (data/hourly.json, offline demo)
        self.market_source = _env("MARKET_SOURCE", "wallex")
        self.replay_speed = float(_env("REPLAY_SPEED", "60"))      # replayed seconds per real second
        self.tick_seconds = int(_env("TICK_SECONDS", "60"))
        self.snapshot_every_s = int(_env("SNAPSHOT_EVERY_S", "300"))
        self.founder_poll_s = int(_env("FOUNDER_POLL_S", "20"))
        self.run_worker = _env("RUN_WORKER", "1") == "1"

        # payments: demo (instant, for testing) | zarinpal
        self.payment_provider = _env("PAYMENT_PROVIDER", "demo")
        self.zarinpal_merchant = _env("ZARINPAL_MERCHANT_ID")
        self.zarinpal_sandbox = _env("ZARINPAL_SANDBOX", "0") == "1"

        self.seed_demo = _env("SEED_DEMO", "0") == "1"
        self.engine_config = load_engine_config()


def load_engine_config() -> dict:
    """The bot's config.yaml is the single source of truth for the strategies (sleeves, fees, capital)."""
    path = _env("ENGINE_CONFIG", os.path.join(ROOT, "config.yaml"))
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as e:
        log.warning("engine config %s not readable (%s): using built-in defaults", path, e)
        return {"challenge": {"initial_capital_tmn": 5_000_000},
                "fees": {"tmn_maker": 0.0025, "tmn_taker": 0.003},
                "portfolio": {"regime_full_pct": 1.0, "sleeves": {
                    "rial": {"capital_pct": 35, "assets": {"BTC": 0.5, "ETH": 0.5}, "stop_pct": 5.0},
                    "beta": {"capital_pct": 45, "assets": {"PEPE": 0.3334, "ADA": 0.3333, "LINK": 0.3333},
                             "universe": ["PEPE", "ADA", "LINK", "SHIB", "DOGE", "LTC", "TRX"], "stop_pct": 7.0}}}}


settings = Settings()
