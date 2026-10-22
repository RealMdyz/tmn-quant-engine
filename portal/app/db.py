"""Database: SQLite on the app's disk by default, PostgreSQL via DATABASE_URL when the platform grows."""
from __future__ import annotations

import time

from sqlalchemy import (JSON, Float, ForeignKey, Integer, String, Text, create_engine, event, func,
                        select)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .settings import settings


class Base(DeclarativeBase):
    pass


def now() -> float:
    return time.time()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")          # user | founder
    created_at: Mapped[float] = mapped_column(Float, default=now)
    last_login_at: Mapped[float] = mapped_column(Float, default=0.0)


class Session_(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[float] = mapped_column(Float, default=now)
    expires_at: Mapped[float] = mapped_column(Float)


class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    answers: Mapped[dict] = mapped_column(JSON)
    capacity: Mapped[float] = mapped_column(Float)
    willingness: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    profile_key: Mapped[str] = mapped_column(String(16))
    alloc_low: Mapped[int] = mapped_column(Integer)
    alloc_medium: Mapped[int] = mapped_column(Integer)
    alloc_high: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_key: Mapped[str] = mapped_column(String(32))
    amount_tmn: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(16))
    authority: Mapped[str] = mapped_column(String(64), default="", index=True)
    ref_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")    # pending | paid | failed
    created_at: Mapped[float] = mapped_column(Float, default=now)
    paid_at: Mapped[float] = mapped_column(Float, default=0.0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_key: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[float] = mapped_column(Float, default=now)
    expires_at: Mapped[float] = mapped_column(Float)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)


class BotAccount(Base):
    """One trading bot per user. mode: paper (simulated on live prices) | master (the real bot on Liara)."""
    __tablename__ = "bot_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    mode: Mapped[str] = mapped_column(String(16), default="paper")
    status: Mapped[str] = mapped_column(String(16), default="stopped")    # stopped | running
    capital_tmn: Mapped[float] = mapped_column(Float, default=0.0)
    alloc_low: Mapped[int] = mapped_column(Integer, default=0)
    alloc_medium: Mapped[int] = mapped_column(Integer, default=0)
    alloc_high: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[float] = mapped_column(Float, default=0.0)
    last_tick_at: Mapped[float] = mapped_column(Float, default=0.0)
    last_snapshot_at: Mapped[float] = mapped_column(Float, default=0.0)


class BotTrade(Base):
    __tablename__ = "bot_trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot_accounts.id", ondelete="CASCADE"), index=True)
    ts: Mapped[float] = mapped_column(Float, default=now)
    sleeve: Mapped[str] = mapped_column(String(16))
    asset: Mapped[str] = mapped_column(String(16))
    side: Mapped[str] = mapped_column(String(4))
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    notional_tmn: Mapped[float] = mapped_column(Float)
    fee_tmn: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, default="")


class BotEvent(Base):
    __tablename__ = "bot_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot_accounts.id", ondelete="CASCADE"), index=True)
    ts: Mapped[float] = mapped_column(Float, default=now)
    kind: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot_accounts.id", ondelete="CASCADE"), index=True)
    ts: Mapped[float] = mapped_column(Float, default=now, index=True)
    equity_tmn: Mapped[float] = mapped_column(Float)
    low_tmn: Mapped[float] = mapped_column(Float, default=0.0)
    medium_tmn: Mapped[float] = mapped_column(Float, default=0.0)
    high_tmn: Mapped[float] = mapped_column(Float, default=0.0)


class KV(Base):
    """Small persistent key/value store (last known bot telemetry, market regime, ...)."""
    __tablename__ = "kv"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[float] = mapped_column(Float, default=now)


_connect_args = {"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args, pool_pre_ping=True)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")      # readers (web) never block the writer (worker)
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    Base.metadata.create_all(engine)


def kv_get(db, key, default=None):
    row = db.get(KV, key)
    return row.value if row else default


def kv_set(db, key, value):
    row = db.get(KV, key)
    if row:
        row.value, row.updated_at = value, now()
    else:
        db.add(KV(key=key, value=value))


def latest_profile(db, user_id):
    return db.scalars(select(RiskProfile).where(RiskProfile.user_id == user_id)
                      .order_by(RiskProfile.id.desc()).limit(1)).first()


def active_subscription(db, user_id):
    return db.scalars(select(Subscription).where(Subscription.user_id == user_id, Subscription.expires_at > now())
                      .order_by(Subscription.expires_at.desc()).limit(1)).first()


def count(db, stmt) -> int:
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
