"""Queries for record sets inside one hosted zone."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, SQLColumnExpression, and_, exists, func, not_, or_, select
from sqlalchemy.orm import Session

from app.domain.enums import RecordType
from app.models import RecordSet, RecordValue
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

_REQUIRED_APEX_TYPES = (RecordType.SOA.value, RecordType.NS.value)
_NEGATED = {
    FilterOperator.NE: FilterOperator.EQ,
    FilterOperator.NOT_CONTAINS: FilterOperator.CONTAINS,
    FilterOperator.NOT_STARTS_WITH: FilterOperator.STARTS_WITH,
}


def _has_value(condition: ColumnElement[bool]) -> ColumnElement[bool]:
    return exists().where(RecordValue.record_set_id == RecordSet.id, condition)


def _value_condition(operator: FilterOperator, value: str) -> ColumnElement[bool]:
    """Match record sets by their values or, for alias records, their alias target."""
    positive = _NEGATED.get(operator, operator)
    matches = or_(
        _has_value(text_condition(RecordValue.value)(positive, value)),
        and_(
            RecordSet.is_alias,
            text_condition(func.coalesce(RecordSet.alias_target_dns_name, ""))(positive, value),
        ),
    )
    return not_(matches) if operator in _NEGATED else matches


def _alias_condition(operator: FilterOperator, value: str) -> ColumnElement[bool]:
    wanted = value.strip().lower() in ("yes", "true", "1")
    matches = RecordSet.is_alias.is_(wanted)
    return not_(matches) if operator is FilterOperator.NE else matches


_FILTER_FIELDS: dict[str, Condition] = {
    "name": fqdn_condition(RecordSet.name),
    "type": text_condition(RecordSet.type),
    "value": _value_condition,
    "ttl": number_condition(RecordSet.ttl),
    "routing_policy": text_condition(RecordSet.routing_policy),
    "set_identifier": text_condition(RecordSet.set_identifier),
    "alias": _alias_condition,
    "id": text_condition(RecordSet.id),
}

_SORT_FIELDS: dict[str, SQLColumnExpression[Any]] = {
    "default": RecordSet.sort_key,
    "name": RecordSet.name,
    "type": RecordSet.type,
    "ttl": RecordSet.ttl,
    "routing_policy": RecordSet.routing_policy,
    "set_identifier": RecordSet.set_identifier.collate("NOCASE"),
    "alias": RecordSet.is_alias,
    "id": RecordSet.id,
}


def list_records(
    db: Session,
    *,
    zone_id: str,
    search: str | None,
    types: Sequence[RecordType],
    filters: Sequence[FilterClause],
    filter_mode: str,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[RecordSet], int]:
    statement = select(RecordSet).where(RecordSet.zone_id == zone_id)
    if search:
        statement = statement.where(
            or_(
                RecordSet.name.ilike(contains_pattern(search), escape=LIKE_ESCAPE),
                _value_condition(FilterOperator.CONTAINS, search),
            )
        )
    if types:
        statement = statement.where(
            RecordSet.type.in_([record_type.value for record_type in types])
        )
    filter_condition = build_filter(filters, _FILTER_FIELDS, filter_mode)
    if filter_condition is not None:
        statement = statement.where(filter_condition)

    total = count_rows(db, statement)
    statement = statement.order_by(
        sort_expression(sort, order, _SORT_FIELDS),
        RecordSet.sort_key,
        RecordSet.type,
        RecordSet.set_identifier,
    )
    return list(db.scalars(page_window(statement, page, page_size))), total


def list_all(db: Session, zone_id: str) -> list[RecordSet]:
    """Every record set of a zone in Route 53's listing order."""
    return list(
        db.scalars(
            select(RecordSet)
            .where(RecordSet.zone_id == zone_id)
            .order_by(RecordSet.sort_key, RecordSet.type, RecordSet.set_identifier)
        )
    )


def get_record(db: Session, zone_id: str, record_id: str) -> RecordSet | None:
    return db.scalar(
        select(RecordSet).where(RecordSet.zone_id == zone_id, RecordSet.id == record_id)
    )


def find_by_identity(
    db: Session, zone_id: str, name: str, record_type: RecordType, set_identifier: str
) -> RecordSet | None:
    return db.scalar(
        select(RecordSet).where(
            RecordSet.zone_id == zone_id,
            RecordSet.name == name,
            RecordSet.type == record_type.value,
            RecordSet.set_identifier == set_identifier,
        )
    )


def list_at_name(db: Session, zone_id: str, name: str) -> list[RecordSet]:
    return list(
        db.scalars(select(RecordSet).where(RecordSet.zone_id == zone_id, RecordSet.name == name))
    )


def count_non_required(db: Session, zone_id: str, zone_name: str) -> int:
    """Record sets other than the apex SOA and NS that Route 53 creates with the zone."""
    required = and_(RecordSet.name == zone_name, RecordSet.type.in_(_REQUIRED_APEX_TYPES))
    return (
        db.scalar(
            select(func.count(RecordSet.id)).where(RecordSet.zone_id == zone_id, not_(required))
        )
        or 0
    )


def apex_name_servers(db: Session, zone_id: str, zone_name: str) -> list[str]:
    record = find_by_identity(db, zone_id, zone_name, RecordType.NS, "")
    return [] if record is None else record.values
