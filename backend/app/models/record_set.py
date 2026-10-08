from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import FailoverRole, RecordType, RoutingPolicy, sql_in_list
from app.domain.record_validation import MAX_TTL
from app.models.base import Base, UtcDateTime, utcnow

if TYPE_CHECKING:
    from app.models.hosted_zone import HostedZone


class RecordSet(Base):
    """A resource record set: every value sharing a name, type and set identifier."""

    __tablename__ = "record_sets"
    __table_args__ = (
        # Simple records store '' as set_identifier so the uniqueness rule also covers them
        # (SQLite treats NULLs as distinct in unique indexes).
        UniqueConstraint(
            "zone_id", "name", "type", "set_identifier", name="uq_record_sets_identity"
        ),
        Index("ix_record_sets_zone_sort", "zone_id", "sort_key", "type"),
        Index("ix_record_sets_zone_type", "zone_id", "type"),
        CheckConstraint(f"type IN ({sql_in_list(RecordType)})", name="type_valid"),
        CheckConstraint(
            f"routing_policy IN ({sql_in_list(RoutingPolicy)})", name="routing_policy_valid"
        ),
        CheckConstraint(
            f"failover IS NULL OR failover IN ({sql_in_list(FailoverRole)})",
            name="failover_valid",
        ),
        CheckConstraint(f"ttl IS NULL OR (ttl >= 0 AND ttl <= {MAX_TTL})", name="ttl_range"),
        CheckConstraint("weight IS NULL OR (weight >= 0 AND weight <= 255)", name="weight_range"),
        CheckConstraint(
            "(is_alias = 1 AND ttl IS NULL AND alias_target_dns_name IS NOT NULL) "
            "OR (is_alias = 0 AND ttl IS NOT NULL AND alias_target_dns_name IS NULL)",
            name="alias_shape",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("hosted_zones.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    sort_key: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(8))
    ttl: Mapped[int | None]

    routing_policy: Mapped[str] = mapped_column(String(16), default=RoutingPolicy.SIMPLE.value)
    set_identifier: Mapped[str] = mapped_column(String(128), default="")
    weight: Mapped[int | None]
    region: Mapped[str | None] = mapped_column(String(32))
    failover: Mapped[str | None] = mapped_column(String(16))
    geo_continent_code: Mapped[str | None] = mapped_column(String(2))
    geo_country_code: Mapped[str | None] = mapped_column(String(2))
    geo_subdivision_code: Mapped[str | None] = mapped_column(String(3))
    health_check_id: Mapped[str | None] = mapped_column(String(64))

    is_alias: Mapped[bool] = mapped_column(Boolean, default=False)
    alias_target_dns_name: Mapped[str | None] = mapped_column(String(255))
    alias_target_hosted_zone_id: Mapped[str | None] = mapped_column(String(32))
    evaluate_target_health: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)

    zone: Mapped["HostedZone"] = relationship(back_populates="record_sets")
    value_rows: Mapped[list["RecordValue"]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecordValue.position",
        lazy="selectin",
    )

    @property
    def values(self) -> list[str]:
        return [row.value for row in self.value_rows]

    def set_values(self, values: list[str]) -> None:
        """Replace the values in place, reusing rows so positions never collide."""
        for position, value in enumerate(values):
            if position < len(self.value_rows):
                self.value_rows[position].value = value
            else:
                self.value_rows.append(RecordValue(position=position, value=value))
        del self.value_rows[len(values) :]


class RecordValue(Base):
    """One value of a record set; ``position`` keeps the order the user entered."""

    __tablename__ = "record_values"
    __table_args__ = (Index("ix_record_values_value", "value"),)

    record_set_id: Mapped[str] = mapped_column(
        ForeignKey("record_sets.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(Text)
