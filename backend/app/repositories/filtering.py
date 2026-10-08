"""Shared query helpers: property filters (``field:operator:value``) and pagination."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Select,
    SQLColumnExpression,
    String,
    and_,
    cast,
    func,
    not_,
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.errors import InvalidInputError

LIKE_ESCAPE = "\\"


class FilterOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    NOT_STARTS_WITH = "not_starts_with"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


@dataclass(frozen=True, slots=True)
class FilterClause:
    field: str
    operator: FilterOperator
    value: str


Condition = Callable[[FilterOperator, str], ColumnElement[bool]]


def parse_filter(raw: str) -> FilterClause:
    parts = raw.split(":", 2)
    if len(parts) != 3 or not parts[0]:
        raise InvalidInputError(
            f"Filter '{raw}' must have the form field:operator:value", field="filter"
        )
    try:
        operator = FilterOperator(parts[1])
    except ValueError:
        raise InvalidInputError(
            f"Filter operator '{parts[1]}' is not supported", field="filter"
        ) from None
    return FilterClause(parts[0], operator, parts[2])


def contains_pattern(value: str) -> str:
    return f"%{_escape_like(value)}%"


def _escape_like(value: str) -> str:
    return (
        value.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


def _unsupported(operator: FilterOperator, kind: str) -> InvalidInputError:
    return InvalidInputError(
        f"Filter operator '{operator}' cannot be used on a {kind} property", field="filter"
    )


def text_condition(column: SQLColumnExpression[Any]) -> Condition:
    """Case-insensitive matching on a text column."""

    def condition(operator: FilterOperator, value: str) -> ColumnElement[bool]:
        match operator:
            case FilterOperator.EQ:
                return func.lower(column) == value.lower()
            case FilterOperator.NE:
                return func.lower(column) != value.lower()
            case FilterOperator.CONTAINS:
                return column.ilike(contains_pattern(value), escape=LIKE_ESCAPE)
            case FilterOperator.NOT_CONTAINS:
                return not_(column.ilike(contains_pattern(value), escape=LIKE_ESCAPE))
            case FilterOperator.STARTS_WITH:
                return column.ilike(f"{_escape_like(value)}%", escape=LIKE_ESCAPE)
            case FilterOperator.NOT_STARTS_WITH:
                return not_(column.ilike(f"{_escape_like(value)}%", escape=LIKE_ESCAPE))
            case _:
                raise _unsupported(operator, "text")

    return condition


def fqdn_condition(column: SQLColumnExpression[Any]) -> Condition:
    """Text matching on a canonical DNS name; exact matches tolerate a missing trailing dot."""
    base = text_condition(column)

    def condition(operator: FilterOperator, value: str) -> ColumnElement[bool]:
        if operator in (FilterOperator.EQ, FilterOperator.NE) and not value.endswith("."):
            value = f"{value}."
        return base(operator, value)

    return condition


def number_condition(column: SQLColumnExpression[Any]) -> Condition:
    def condition(operator: FilterOperator, value: str) -> ColumnElement[bool]:
        if operator is FilterOperator.CONTAINS:
            return cast(column, String).like(contains_pattern(value), escape=LIKE_ESCAPE)
        try:
            number = int(value)
        except ValueError:
            raise InvalidInputError(
                f"Filter value '{value}' must be a whole number", field="filter"
            ) from None
        match operator:
            case FilterOperator.EQ:
                return column == number
            case FilterOperator.NE:
                return column != number
            case FilterOperator.GT:
                return column > number
            case FilterOperator.GTE:
                return column >= number
            case FilterOperator.LT:
                return column < number
            case FilterOperator.LTE:
                return column <= number
            case _:
                raise _unsupported(operator, "numeric")

    return condition


def build_filter(
    clauses: Sequence[FilterClause], fields: Mapping[str, Condition], mode: str
) -> ColumnElement[bool] | None:
    """Combine filter clauses with AND or OR; returns ``None`` when there are none."""
    conditions = []
    for clause in clauses:
        condition = fields.get(clause.field)
        if condition is None:
            raise InvalidInputError(
                f"Cannot filter by '{clause.field}'. Supported properties: "
                f"{', '.join(sorted(fields))}",
                field="filter",
            )
        conditions.append(condition(clause.operator, clause.value))
    if not conditions:
        return None
    return or_(*conditions) if mode == "or" else and_(*conditions)


def sort_expression(
    sort: str, order: str, fields: Mapping[str, SQLColumnExpression[Any]]
) -> ColumnElement[Any]:
    column = fields.get(sort)
    if column is None:
        raise InvalidInputError(
            f"Cannot sort by '{sort}'. Supported properties: {', '.join(sorted(fields))}",
            field="sort",
        )
    return column.desc() if order == "desc" else column.asc()


def count_rows(db: Session, statement: Select[Any]) -> int:
    subquery = statement.order_by(None).subquery()
    return db.scalar(select(func.count()).select_from(subquery)) or 0


def page_window(statement: Select[Any], page: int, page_size: int) -> Select[Any]:
    return statement.limit(page_size).offset((page - 1) * page_size)
