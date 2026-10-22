"""SEED_DEMO=1: a few demo investors (one per risk profile) with demo subscriptions and running paper bots,
so the platform pages have something to show on a fresh server. Never enable it on the real platform."""
from __future__ import annotations

import logging

from sqlalchemy import select

from . import billing, risk, simulator
from .db import BotAccount, RiskProfile, SessionLocal, User
from .security import hash_password
from .settings import settings

log = logging.getLogger("portal.seed")

DEMO = [  # name, answers (0..4 per question, in QUESTIONS order), capital
    ("سارا (نمونه)", [1, 1, 2, 2, 2, 0, 0, 0, 1, 1], 20_000_000),
    ("علی (نمونه)", [2, 2, 2, 3, 3, 1, 2, 1, 1, 2], 50_000_000),
    ("مریم (نمونه)", [3, 3, 3, 3, 3, 2, 2, 2, 2, 2], 100_000_000),
    ("رضا (نمونه)", [4, 3, 3, 4, 4, 3, 3, 3, 3, 3], 80_000_000),
    ("نیما (نمونه)", [4, 4, 4, 4, 4, 4, 4, 4, 4, 4], 30_000_000),
]


def seed_demo():
    with SessionLocal() as db:
        if db.scalars(select(User).where(User.email.like("demo%@example.com"))).first():
            return
        for i, (name, vals, capital) in enumerate(DEMO, 1):
            u = User(email=f"demo{i}@example.com", name=name, password_hash=hash_password(f"demo-pass-{i}"))
            db.add(u)
            db.flush()
            answers = {q["id"]: v for q, v in zip(risk.QUESTIONS, vals)}
            r = risk.score(answers)
            a = r["allocation"]
            db.add(RiskProfile(user_id=u.id, answers=answers, capacity=r["capacity"], willingness=r["willingness"],
                               score=r["score"], profile_key=r["profile_key"], alloc_low=a["low"],
                               alloc_medium=a["medium"], alloc_high=a["high"]))
            if settings.payment_provider == "demo":
                billing.start_payment(db, u, ["monthly", "quarterly", "yearly"][i % 3])
            bot = BotAccount(user_id=u.id)
            db.add(bot)
            db.flush()
            ctx = simulator.start(bot, capital, a)
            db.add_all(ctx.events)
        db.commit()
    log.info("demo investors seeded")
