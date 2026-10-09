from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import RecordType
from app.schemas.common import ErrorDetail

ExportFormat = Literal["bind", "json"]
ImportStatus = Literal["create", "replace", "skip", "error"]

MAX_ZONE_FILE_LENGTH = 1_000_000


class ZoneFileImportRequest(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_ZONE_FILE_LENGTH)
    dry_run: bool = Field(default=True, description="Validate and preview without saving")
    replace_existing: bool = Field(
        default=False, description="Overwrite record sets that already exist in the zone"
    )


class ImportedRecordSet(BaseModel):
    line: int
    name: str
    type: RecordType
    ttl: int
    values: list[str]
    status: ImportStatus
    reason: str | None = None


class ImportSummary(BaseModel):
    create: int = 0
    replace: int = 0
    skip: int = 0
    error: int = 0


class ZoneFileImportResult(BaseModel):
    dry_run: bool
    applied: bool
    summary: ImportSummary
    record_sets: list[ImportedRecordSet]
    errors: list[ErrorDetail] = Field(description="Syntax errors, by zone file line")
    change_id: str | None = Field(
        default=None, description="ID of the change that imported the records; none for a preview"
    )
