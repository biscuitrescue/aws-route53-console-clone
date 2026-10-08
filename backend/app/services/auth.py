"""Mock sign-in: password check, opaque session tokens, expiry."""

import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import UnauthorizedError
from app.models import AuthSession, User
from app.models.base import utcnow

_TOKEN_BYTES = 32
_LAST_SEEN_RESOLUTION = timedelta(minutes=5)
_hasher = PasswordHasher()
# Verified against when the account does not exist, so both failures take the same time.
_PLACEHOLDER_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login(db: Session, settings: Settings, email: str, password: str) -> tuple[str, AuthSession]:
    """Check credentials and open a session; returns the raw token for the cookie."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    password_ok = _verify_password(user.password_hash if user else _PLACEHOLDER_HASH, password)
    if user is None or not password_ok:
        raise UnauthorizedError(
            "Your authentication information is incorrect. Please try again.",
            code="AuthFailure",
        )

    now = utcnow()
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    session = AuthSession(
        token_hash=_hash_token(token),
        user=user,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(session)
    db.commit()
    return token, session


def authenticate(db: Session, token: str | None) -> AuthSession:
    """Resolve a cookie token to its live session or raise ``UnauthorizedError``."""
    if not token:
        raise UnauthorizedError("You are not signed in.")
    session = db.get(AuthSession, _hash_token(token))
    now = utcnow()
    if session is None or session.expires_at <= now:
        raise UnauthorizedError("Your session has expired. Sign in again.", code="SessionExpired")
    if now - session.last_seen_at >= _LAST_SEEN_RESOLUTION:
        session.last_seen_at = now
        db.commit()
    return session


def logout(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _hash_token(token)))
        db.commit()
