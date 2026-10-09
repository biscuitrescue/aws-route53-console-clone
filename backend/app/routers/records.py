from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Response, status

from app.dependencies import CurrentZone, DbSession, SettingsDep
from app.domain.enums import RecordType
from app.routers.responses import (
    BAD_REQUEST,
    CONFLICT,
    NOT_FOUND,
    UNAUTHORIZED,
    FilterModeParam,
    Filters,
    Order,
    PageNumber,
    PageSize,
    Search,
    paginate,
)
from app.schemas.common import Page
from app.schemas.record_set import (
    ChangeBatchRequest,
    ChangeBatchResult,
    RecordSetInput,
    RecordSetOut,
    RecordSetUpdate,
)
from app.services import changes as change_service
from app.services import records as record_service

router = APIRouter(
    prefix="/hostedzones/{zone_id}",
    tags=["Records"],
    responses={**UNAUTHORIZED, **NOT_FOUND},
)

RecordId = Annotated[str, Path(description="Record ID")]

# Single-record routes answer with the record itself, so the ID of the change they made
# travels in this header. Ask `GET /changes/{id}` for its status.
CHANGE_ID_HEADER = "X-Change-Id"
_CHANGE_HEADER_DOC: dict[str, Any] = {
    "headers": {
        CHANGE_ID_HEADER: {
            "description": "ID of the change this request made; see `GET /changes/{change_id}`",
            "schema": {"type": "string"},
        }
    }
}


@router.get("/records", summary="List the records of a hosted zone", responses=BAD_REQUEST)
def list_records(
    db: DbSession,
    zone: CurrentZone,
    search: Search = None,
    types: Annotated[
        list[RecordType], Query(alias="type", description="Only these record types; repeatable")
    ] = [],  # noqa: B006
    filters: Filters = [],  # noqa: B006
    filter_mode: FilterModeParam = "and",
    sort: Annotated[
        str,
        Query(
            description="default (Route 53 order), name, type, ttl, routing_policy, "
            "differentiator, set_identifier, alias, value, health_check_id, "
            "evaluate_target_health or id"
        ),
    ] = "default",
    order: Order = "asc",
    page: PageNumber = 1,
    page_size: PageSize = 50,
) -> Page[RecordSetOut]:
    records, total = record_service.list_records(
        db,
        zone,
        search=search,
        types=types,
        filters=filters,
        filter_mode=filter_mode,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    return paginate([RecordSetOut.from_model(record) for record in records], total, page, page_size)


@router.post(
    "/records",
    status_code=status.HTTP_201_CREATED,
    summary="Create a record",
    responses={**BAD_REQUEST, **CONFLICT, 201: _CHANGE_HEADER_DOC},
)
def create_record(
    payload: RecordSetInput,
    response: Response,
    db: DbSession,
    zone: CurrentZone,
    settings: SettingsDep,
) -> RecordSetOut:
    record, change = record_service.create_record(
        db, zone, payload, max_records=settings.max_records_per_zone
    )
    response.headers[CHANGE_ID_HEADER] = change.id
    return RecordSetOut.from_model(record)


@router.post(
    "/records:batch",
    summary="Apply a change batch atomically",
    description="CREATE, UPSERT and DELETE changes run in order in one transaction, like "
    "`ChangeResourceRecordSets`. If any change is invalid, none is applied and every "
    "failure is listed in `details` with the index of its change.\n\n"
    "The answer carries the change's `id` and its `status`, which starts as `PENDING`; "
    "`GET /changes/{change_id}` reports it afterwards.",
    responses=BAD_REQUEST,
)
def change_records(
    payload: ChangeBatchRequest, db: DbSession, zone: CurrentZone, settings: SettingsDep
) -> ChangeBatchResult:
    outcome = record_service.apply_batch(
        db,
        zone,
        payload.changes,
        comment=payload.comment,
        max_records=settings.max_records_per_zone,
    )
    change = outcome.change
    assert change is not None
    return ChangeBatchResult(
        id=change.id,
        status=change_service.status_of(change, settings),
        comment=change.comment,
        submitted_at=change.submitted_at,
        created=outcome.created,
        updated=outcome.updated,
        deleted=outcome.deleted,
        record_sets=[RecordSetOut.from_model(record) for record in outcome.record_sets],
    )


@router.get("/records/{record_id}", summary="Get a record")
def get_record(record_id: RecordId, db: DbSession, zone: CurrentZone) -> RecordSetOut:
    return RecordSetOut.from_model(record_service.get_record(db, zone, record_id))


@router.patch(
    "/records/{record_id}",
    summary="Edit a record",
    description="Omitted fields keep their value. The apex NS and SOA records can be edited "
    "but not renamed or retyped.",
    responses={**BAD_REQUEST, **CONFLICT, 200: _CHANGE_HEADER_DOC},
)
def update_record(
    record_id: RecordId,
    payload: RecordSetUpdate,
    response: Response,
    db: DbSession,
    zone: CurrentZone,
) -> RecordSetOut:
    record, change = record_service.update_record(db, zone, record_id, payload)
    response.headers[CHANGE_ID_HEADER] = change.id
    return RecordSetOut.from_model(record)


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a record",
    description="The apex NS and SOA records cannot be deleted.",
    responses={**BAD_REQUEST, 204: _CHANGE_HEADER_DOC},
)
def delete_record(
    record_id: RecordId, response: Response, db: DbSession, zone: CurrentZone
) -> None:
    response.headers[CHANGE_ID_HEADER] = record_service.delete_record(db, zone, record_id).id
