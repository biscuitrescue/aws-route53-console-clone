from typing import Literal

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = Field(default=None, description="Request field the problem relates to")
    index: int | None = Field(default=None, description="Position of the failing batch change")
    line: int | None = Field(default=None, description="Zone file line the problem relates to")
    message: str


class ErrorResponse(BaseModel):
    code: str = Field(examples=["NoSuchHostedZone"])
    message: str
    details: list[ErrorDetail] = []


class Page[ItemT](BaseModel):
    items: list[ItemT]
    total: int = Field(description="Number of items matching the query across all pages")
    page: int
    page_size: int
    pages: int


SortOrder = Literal["asc", "desc"]
FilterMode = Literal["and", "or"]
