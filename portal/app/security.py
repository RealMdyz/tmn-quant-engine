"""Passwords (scrypt), server-side sessions (random token, only its hash stored) and a login rate limit."""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import threading
import time

from .db import Session_, User, now
from .settings import settings

COOKIE = "tmn_session"
_N, _R, _P = 2 ** 14, 8, 1


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${base64.b64encode(salt).decode()}${base64.b64encode(h).decode()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(got, base64.b64decode(h))
    except (ValueError, TypeError):
        return False


def password_problem(pw: str) -> str | None:
    if len(pw) < 8:
        return "رمز عبور باید حداقل ۸ کاراکتر باشد"
    if pw.isdigit() or pw.isalpha():
        return "رمز عبور باید ترکیبی از حرف و عدد باشد"
    return None


EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,120}\.[A-Za-z]{2,24}$")


def _token_hash(token: str) -> str:
    return hashlib.sha256((settings.secret + token).encode()).hexdigest()


def create_session(db, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(Session_(token_hash=_token_hash(token), user_id=user.id, expires_at=now() + settings.session_days * 86400))
    user.last_login_at = now()
    return token


def user_from_token(db, token: str | None) -> User | None:
    if not token:
        return None
    s = db.get(Session_, _token_hash(token))
    if not s or s.expires_at < now():
        return None
    return db.get(User, s.user_id)


def drop_session(db, token: str | None):
    if token:
        s = db.get(Session_, _token_hash(token))
        if s:
            db.delete(s)


class RateLimit:
    """At most `limit` failed attempts per key in `window` seconds (in memory; one app instance)."""

    def __init__(self, limit=8, window=900):
        self.limit, self.window = limit, window
        self.hits: dict[str, list[float]] = {}
        self.lock = threading.Lock()

    def blocked(self, key: str) -> bool:
        with self.lock:
            t = time.time()
            self.hits[key] = [x for x in self.hits.get(key, []) if t - x < self.window]
            return len(self.hits[key]) >= self.limit

    def fail(self, key: str):
        with self.lock:
            self.hits.setdefault(key, []).append(time.time())

    def reset(self, key: str):
        with self.lock:
            self.hits.pop(key, None)


login_limit = RateLimit()
