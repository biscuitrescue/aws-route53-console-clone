from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import UserKind, sql_in_list
from app.models.base import Base, UtcDateTime, utcnow


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"kind IN ({sql_in_list(UserKind)})", name="kind_valid"),
        # Finding the sandboxes that have gone idle, oldest first.
        Index("ix_users_kind_last_seen_at", "kind", "last_seen_at"),
        # Sandboxes come and go; AUTOINCREMENT keeps a deleted one's ID from being reused.
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(64))
    account_id: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    kind: Mapped[str] = mapped_column(String(16), default=UserKind.ACCOUNT.value)
    # SHA-256 of the sandbox cookie; set only for sandboxes.
    sandbox_key_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

    @property
    def is_sandbox(self) -> bool:
        return self.kind == UserKind.SANDBOX.value


class AuthSession(Base):
    """A login session. Only the SHA-256 of the cookie token is stored."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_expires_at", "expires_at"),)

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    last_seen_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    user: Mapped[User] = relationship(lazy="joined")
