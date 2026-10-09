from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UtcDateTime, utcnow


class Change(Base):
    """One accepted change to a zone's records, kept so its status can be asked for.

    The status itself is not stored: it follows from how long ago the change was
    submitted (see ``app.services.changes``).
    """

    __tablename__ = "changes"
    __table_args__ = (Index("ix_changes_zone_submitted_at", "zone_id", "submitted_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("hosted_zones.id", ondelete="CASCADE"))
    comment: Mapped[str] = mapped_column(String(256), default="")
    submitted_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
