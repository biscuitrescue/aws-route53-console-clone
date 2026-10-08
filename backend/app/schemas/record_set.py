from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field

from app.domain.enums import ChangeAction, FailoverRole, RecordType, RoutingPolicy
from app.models import RecordSet


class GeoLocation(BaseModel):
    continent_code: str | None = Field(default=None, max_length=2)
    country_code: str | None = Field(default=None, max_length=2)
    subdivision_code: str | None = Field(default=None, max_length=3)


class AliasTarget(BaseModel):
    dns_name: str = Field(min_length=1, max_length=255)
    hosted_zone_id: str = Field(min_length=1, max_length=32)
    evaluate_target_health: bool = False


class RecordSetInput(BaseModel):
    """A complete record set, as accepted by create and by change batches."""

    name: str = Field(
        default="",
        max_length=1024,
        description="Relative to the zone (`www`), fully qualified, or empty / `@` for the apex",
    )
    type: RecordType
    ttl: int | None = Field(default=None, description="Seconds; required unless alias")
    values: list[str] = Field(default=[], description="One entry per value; empty for alias")
    routing_policy: RoutingPolicy = RoutingPolicy.SIMPLE
    set_identifier: str | None = Field(default=None, max_length=128)
    weight: int | None = None
    region: str | None = Field(default=None, max_length=32)
    failover: FailoverRole | None = None
    geolocation: GeoLocation | None = None
    health_check_id: str | None = Field(default=None, max_length=64)
    alias_target: AliasTarget | None = None


class RecordSetUpdate(BaseModel):
    """Partial update; omitted fields keep their current value."""

    name: str | None = Field(default=None, max_length=1024)
    type: RecordType | None = None
    ttl: int | None = None
    values: list[str] | None = None
    routing_policy: RoutingPolicy | None = None
    set_identifier: str | None = Field(default=None, max_length=128)
    weight: int | None = None
    region: str | None = Field(default=None, max_length=32)
    failover: FailoverRole | None = None
    geolocation: GeoLocation | None = None
    health_check_id: str | None = Field(default=None, max_length=64)
    alias_target: AliasTarget | None = None


class RecordSetOut(BaseModel):
    id: str
    zone_id: str
    name: str = Field(description="Canonical FQDN with trailing dot", examples=["www.example.com."])
    type: RecordType
    ttl: int | None
    values: list[str]
    routing_policy: RoutingPolicy
    set_identifier: str | None
    weight: int | None
    region: str | None
    failover: FailoverRole | None
    geolocation: GeoLocation | None
    health_check_id: str | None
    alias: bool
    alias_target: AliasTarget | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, record: RecordSet) -> Self:
        geolocation = None
        if record.geo_continent_code or record.geo_country_code:
            geolocation = GeoLocation(
                continent_code=record.geo_continent_code,
                country_code=record.geo_country_code,
                subdivision_code=record.geo_subdivision_code,
            )
        alias_target = None
        if record.is_alias and record.alias_target_dns_name:
            alias_target = AliasTarget(
                dns_name=record.alias_target_dns_name,
                hosted_zone_id=record.alias_target_hosted_zone_id or "",
                evaluate_target_health=record.evaluate_target_health,
            )
        return cls(
            id=record.id,
            zone_id=record.zone_id,
            name=record.name,
            type=RecordType(record.type),
            ttl=record.ttl,
            values=record.values,
            routing_policy=RoutingPolicy(record.routing_policy),
            set_identifier=record.set_identifier or None,
            weight=record.weight,
            region=record.region,
            failover=FailoverRole(record.failover) if record.failover else None,
            geolocation=geolocation,
            health_check_id=record.health_check_id,
            alias=record.is_alias,
            alias_target=alias_target,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class Change(BaseModel):
    action: ChangeAction
    record_set: RecordSetInput


class ChangeBatchRequest(BaseModel):
    comment: str = Field(default="", max_length=256)
    changes: list[Change] = Field(min_length=1, max_length=1000)


class ChangeBatchResult(BaseModel):
    status: str = Field(default="INSYNC", description="Changes apply immediately in the clone")
    comment: str
    submitted_at: datetime
    created: int
    updated: int
    deleted: int
    record_sets: list[RecordSetOut] = Field(description="Record sets created or updated")
