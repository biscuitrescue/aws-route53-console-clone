from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies import CurrentUser, CurrentZoneRow, DbSession, SettingsDep, ZoneId
from app.domain.enums import ZoneType
from app.repositories.hosted_zones import ZoneRow
from app.routers.responses import (
    BAD_REQUEST,
    CONFLICT,
    UNAUTHORIZED,
    ZONE_NOT_FOUND,
    FilterModeParam,
    Filters,
    Order,
    PageNumber,
    PageSize,
    Search,
    paginate,
)
from app.schemas.common import Page
from app.schemas.hosted_zone import (
    HostedZoneCreate,
    HostedZoneDetail,
    HostedZoneSummary,
    HostedZoneUpdate,
    Tag,
    TagList,
    TagsUpdate,
    VpcAssociation,
)
from app.services import hosted_zones as zone_service

router = APIRouter(prefix="/hostedzones", tags=["Hosted zones"], responses=UNAUTHORIZED)


def _summary(row: ZoneRow) -> HostedZoneSummary:
    zone = row.zone
    return HostedZoneSummary(
        id=zone.id,
        name=zone.name,
        type=ZoneType(zone.type),
        description=zone.description,
        created_by=zone.created_by,
        record_count=row.record_count,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


def _detail(row: ZoneRow) -> HostedZoneDetail:
    zone = row.zone
    return HostedZoneDetail(
        **_summary(row).model_dump(),
        caller_reference=zone.caller_reference,
        name_servers=row.name_servers,
        vpcs=[VpcAssociation.model_validate(vpc) for vpc in zone.vpcs],
        tags=[Tag.model_validate(tag) for tag in zone.tags],
    )


@router.get("", summary="List hosted zones", responses=BAD_REQUEST)
def list_hosted_zones(
    db: DbSession,
    user: CurrentUser,
    search: Search = None,
    zone_type: Annotated[
        ZoneType | None, Query(alias="type", description="Only zones of this type")
    ] = None,
    filters: Filters = [],  # noqa: B006
    filter_mode: FilterModeParam = "and",
    sort: Annotated[
        str,
        Query(
            description="default (Route 53 order), name, type, description, id, created_by, "
            "record_count or created_at"
        ),
    ] = "default",
    order: Order = "asc",
    page: PageNumber = 1,
    page_size: PageSize = 50,
) -> Page[HostedZoneSummary]:
    rows, total = zone_service.list_zones(
        db,
        user,
        search=search,
        zone_type=zone_type,
        filters=filters,
        filter_mode=filter_mode,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    return paginate([_summary(row) for row in rows], total, page, page_size)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a hosted zone",
    description="Also creates the apex NS and SOA record sets, as Route 53 does.",
    responses=BAD_REQUEST,
)
def create_hosted_zone(
    payload: HostedZoneCreate, db: DbSession, user: CurrentUser, settings: SettingsDep
) -> HostedZoneDetail:
    return _detail(zone_service.create_zone(db, user, payload, max_zones=settings.max_hosted_zones))


@router.get("/{zone_id}", summary="Get a hosted zone", responses=ZONE_NOT_FOUND)
def get_hosted_zone(row: CurrentZoneRow) -> HostedZoneDetail:
    return _detail(row)


@router.patch(
    "/{zone_id}",
    summary="Edit a hosted zone",
    description="The description, the tags and, for a private zone, the VPC associations can "
    "be changed after a zone is created. Omitted fields keep their value; the edit is "
    "applied as a whole or not at all.",
    responses={**ZONE_NOT_FOUND, **BAD_REQUEST},
)
def update_hosted_zone(
    zone_id: ZoneId, payload: HostedZoneUpdate, db: DbSession, user: CurrentUser
) -> HostedZoneDetail:
    return _detail(zone_service.update_zone(db, user, zone_id, payload))


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a hosted zone",
    description="Fails with `HostedZoneNotEmpty` while the zone has records besides the apex "
    "NS and SOA.",
    responses={**ZONE_NOT_FOUND, **CONFLICT},
)
def delete_hosted_zone(zone_id: ZoneId, db: DbSession, user: CurrentUser) -> None:
    zone_service.delete_zone(db, user, zone_id)


@router.get(
    "/{zone_id}/tags", tags=["Tags"], summary="List a zone's tags", responses=ZONE_NOT_FOUND
)
def list_tags(row: CurrentZoneRow) -> TagList:
    return TagList(tags=[Tag.model_validate(tag) for tag in row.zone.tags])


@router.put(
    "/{zone_id}/tags",
    tags=["Tags"],
    summary="Replace a zone's tags",
    responses={**ZONE_NOT_FOUND, **BAD_REQUEST},
)
def replace_tags(zone_id: ZoneId, payload: TagsUpdate, db: DbSession, user: CurrentUser) -> TagList:
    tags = zone_service.replace_tags(db, user, zone_id, payload.tags)
    return TagList(tags=[Tag.model_validate(tag) for tag in tags])
