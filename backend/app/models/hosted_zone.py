from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ZoneType, sql_in_list
from app.models.base import Base, UtcDateTime, utcnow

if TYPE_CHECKING:
    from app.models.record_set import RecordSet


class HostedZone(Base):
    __tablename__ = "hosted_zones"
    __table_args__ = (CheckConstraint(f"type IN ({sql_in_list(ZoneType)})", name="type_valid"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    type: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(256), default="")
    caller_reference: Mapped[str] = mapped_column(String(128), unique=True)
    created_by: Mapped[str] = mapped_column(String(64), default="Route 53")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)

    vpcs: Mapped[list["HostedZoneVpc"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="HostedZoneVpc.id"
    )
    tags: Mapped[list["HostedZoneTag"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="HostedZoneTag.key"
    )
    record_sets: Mapped[list["RecordSet"]] = relationship(
        back_populates="zone", cascade="all, delete-orphan", passive_deletes=True
    )


class HostedZoneVpc(Base):
    """A VPC associated with a private hosted zone."""

    __tablename__ = "hosted_zone_vpcs"
    __table_args__ = (UniqueConstraint("zone_id", "vpc_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("hosted_zones.id", ondelete="CASCADE"))
    vpc_id: Mapped[str] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(32))


class HostedZoneTag(Base):
    __tablename__ = "hosted_zone_tags"
    __table_args__ = (UniqueConstraint("zone_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("hosted_zones.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(String(256), default="")
