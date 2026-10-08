from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from app.dependencies import CurrentZone, CurrentZoneRow, DbSession
from app.routers.responses import BAD_REQUEST, UNAUTHORIZED, ZONE_NOT_FOUND
from app.schemas.transfer import ExportFormat, ZoneFileImportRequest, ZoneFileImportResult
from app.services import zone_transfer

router = APIRouter(
    prefix="/hostedzones/{zone_id}",
    tags=["Import and export"],
    responses={**UNAUTHORIZED, **ZONE_NOT_FOUND},
)


def _attachment(zone_name: str, extension: str) -> dict[str, str]:
    filename = f"{zone_name.removesuffix('.')}.{extension}"
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


@router.get(
    "/export",
    summary="Export a hosted zone",
    description="`bind` returns a zone file; `json` returns the zone and its record sets in "
    "the shape of the AWS CLI's `list-resource-record-sets`.",
    response_class=Response,
    responses={
        200: {
            "content": {"text/plain": {}, "application/json": {}},
            "description": "The exported zone as a file download",
        }
    },
)
def export_zone(
    db: DbSession,
    row: CurrentZoneRow,
    export_format: Annotated[ExportFormat, Query(alias="format")] = "bind",
) -> Response:
    if export_format == "json":
        return JSONResponse(
            zone_transfer.export_json(db, row), headers=_attachment(row.zone.name, "json")
        )
    return PlainTextResponse(
        zone_transfer.export_bind(db, row), headers=_attachment(row.zone.name, "zone")
    )


@router.post(
    "/import",
    summary="Import records from a BIND zone file",
    description="With `dry_run` (the default) the file is parsed and validated and a preview "
    "is returned. Without it the records are created in one atomic change batch; the apex "
    "NS and SOA in the file are skipped.",
    responses=BAD_REQUEST,
)
def import_zone_file(
    payload: ZoneFileImportRequest, db: DbSession, zone: CurrentZone
) -> ZoneFileImportResult:
    return zone_transfer.import_zone_file(db, zone, payload)
