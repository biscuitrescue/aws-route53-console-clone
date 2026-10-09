"""Documented error responses and pagination parameters shared by the routers."""

import math
from typing import Annotated, Any

from fastapi import Query

from app.schemas.common import ErrorResponse, FilterMode, Page, SortOrder

MAX_PAGE_SIZE = 500

UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not signed in or the session expired"},
}
BAD_REQUEST: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "The request violates a Route 53 rule"},
    422: {"model": ErrorResponse, "description": "The request body or parameters are malformed"},
}
ZONE_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "The hosted zone does not exist"},
}
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "The hosted zone or record does not exist"},
}
CONFLICT: dict[int | str, dict[str, Any]] = {
    409: {"model": ErrorResponse, "description": "The change conflicts with existing data"},
}

TOO_MANY_REQUESTS: dict[int | str, dict[str, Any]] = {
    429: {"model": ErrorResponse, "description": "Too many failed attempts; see `Retry-After`"},
}

PageNumber = Annotated[int, Query(ge=1, description="1-based page number")]
PageSize = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page")]
Search = Annotated[
    str | None, Query(max_length=255, description="Free-text search across the main columns")
]
Filters = Annotated[
    list[str],
    Query(
        alias="filter",
        description=(
            "Property filter as `field:operator:value`, repeatable. Operators: eq, ne, "
            "contains, not_contains, starts_with, not_starts_with, gt, gte, lt, lte."
        ),
        examples=["name:contains:shop"],
    ),
]
FilterModeParam = Annotated[
    FilterMode, Query(description="Whether all filters must match or any of them")
]
Order = Annotated[SortOrder, Query(description="Sort direction")]


def paginate[ItemT](items: list[ItemT], total: int, page: int, page_size: int) -> Page[ItemT]:
    return Page[ItemT](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )
