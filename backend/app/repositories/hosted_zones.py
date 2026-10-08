"""Queries for hosted zones. The record count is always derived, never stored."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, SQLColumnExpression, func, not_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import ZoneType
from app.errors import InvalidInputError
from app.models import HostedZone, RecordSet
from app.repositories import records as record_repository
from app.repositories.filtering import (
    LIKE_ESCAPE,
    Condition,
    FilterClause,
    FilterOperator,
    build_filter,
    contains_pattern,
    count_rows,
    fqdn_condition,
    number_condition,
    page_window,
    sort_expression,
    text_condition,
)

_RECORD_COUNT = (
    select(func.count(RecordSet.id))
    .where(RecordSet.zone_id == HostedZone.id)
    .correlate(HostedZone)
    .scalar_subquery()
)


def _any_condition(operator: FilterOperator, value: str) -> ColumnElement[bool]:
    """Free text: match the name, description or ID."""
    negated = operator is FilterOperator.NOT_CONTAINS
    if operator not in (FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS):
        raise InvalidInputError("Free-text filters support only contains", field="filter")
    pattern = contains_pattern(value)
    matches = or_(
        HostedZone.name.ilike(pattern, escape=LIKE_ESCAPE),
        HostedZone.description.ilike(pattern, escape=LIKE_ESCAPE),
        HostedZone.id.ilike(pattern, escape=LIKE_ESCAPE),
    )
    return not_(matches) if negated else matches


_FILTER_FIELDS: dict[str, Condition] = {
    "any": _any_condition,
    "name": fqdn_condition(HostedZone.name),
    "type": text_condition(HostedZone.type),
    "description": text_condition(HostedZone.description),
    "id": text_condition(HostedZone.id),
    "created_by": text_condition(HostedZone.created_by),
    "record_count": number_condition(_RECORD_COUNT),
}

# Names sort the way Route 53 lists them: by domain, parent before child.
_SORT_FIELDS: dict[str, SQLColumnExpression[Any]] = {
    "name": HostedZone.sort_key,
    "type": HostedZone.type,
    "description": HostedZone.description.collate("NOCASE"),
    "id": HostedZone.id,
    "created_by": HostedZone.created_by.collate("NOCASE"),
    "record_count": _RECORD_COUNT,
    "created_at": HostedZone.created_at,
}


@dataclass(frozen=True, slots=True)
class ZoneRow:
    zone: HostedZone
    record_count: int
    name_servers: list[str] = field(default_factory=list)


def list_zones(
    db: Session,
    *,
    owner_id: int,
    search: str | None,
    zone_type: ZoneType | None,
    filters: Sequence[FilterClause],
    filter_mode: str,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[ZoneRow], int]:
    statement = select(HostedZone, _RECORD_COUNT.label("record_count")).where(
        HostedZone.owner_id == owner_id
    )
    if search:
        statement = statement.where(_any_condition(FilterOperator.CONTAINS, search))
    if zone_type is not None:
        statement = statement.where(HostedZone.type == zone_type.value)
    filter_condition = build_filter(filters, _FILTER_FIELDS, filter_mode)
    if filter_condition is not None:
        statement = statement.where(filter_condition)

    total = count_rows(db, statement)
    statement = statement.order_by(
        sort_expression(sort, order, _SORT_FIELDS), HostedZone.created_at, HostedZone.id
    )
    rows = db.execute(page_window(statement, page, page_size)).all()
    return [ZoneRow(zone, record_count) for zone, record_count in rows], total


def get_zone(db: Session, *, owner_id: int, zone_id: str) -> ZoneRow | None:
    row = db.execute(
        select(HostedZone, _RECORD_COUNT.label("record_count"))
        .where(HostedZone.id == zone_id, HostedZone.owner_id == owner_id)
        .options(selectinload(HostedZone.vpcs), selectinload(HostedZone.tags))
    ).one_or_none()
    if row is None:
        return None
    zone, record_count = row
    return ZoneRow(zone, record_count, record_repository.apex_name_servers(db, zone.id, zone.name))


def count_owned(db: Session, owner_id: int) -> int:
    return db.scalar(select(func.count(HostedZone.id)).where(HostedZone.owner_id == owner_id)) or 0
