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
# Argon2id with OWASP's baseline parameters: 19 MiB of memory, two passes, one lane. The
# library default (64 MiB, three passes, four lanes) took 190 ms per sign-in on the 1 GB,
# two-vCPU server this runs on and a fifth of its free memory; this takes about 40 ms.
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
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


def verify_credentials(db: Session, email: str, password: str) -> User:
    """Return the account the credentials belong to or raise ``UnauthorizedError``."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    password_ok = _verify_password(user.password_hash if user else _PLACEHOLDER_HASH, password)
    if user is None or not password_ok:
        raise UnauthorizedError(
            "Your authentication information is incorrect. Please try again.",
            code="AuthFailure",
        )
    # A hash made with older parameters is replaced now that the password is known.
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


def open_session(db: Session, settings: Settings, user: User) -> tuple[str, AuthSession]:
    """Start a session for ``user``; returns the raw token for the cookie."""
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


def login(db: Session, settings: Settings, email: str, password: str) -> tuple[str, AuthSession]:
    """Check credentials and open a session; returns the raw token for the cookie."""
    return open_session(db, settings, verify_credentials(db, email, password))


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
