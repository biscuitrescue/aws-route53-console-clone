"""Use cases for hosted zones, their tags and VPC associations."""

import re
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.aws_regions import AWS_REGIONS
from app.domain.dns_names import DnsNameError, normalize_zone_name, sort_key
from app.domain.enums import RecordType, ZoneType
from app.domain.identifiers import (
    APEX_NS_TTL,
    APEX_SOA_TTL,
    new_caller_reference,
    new_delegation_set,
    new_hosted_zone_id,
    soa_value,
)
from app.errors import (
    ConflictError,
    InvalidDomainNameError,
    InvalidInputError,
    LimitExceededError,
    NotFoundError,
)
from app.models import HostedZone, HostedZoneTag, HostedZoneVpc, User
from app.models.base import utcnow
from app.repositories import hosted_zones as zone_repository
from app.repositories import records as record_repository
from app.repositories.filtering import parse_filter
from app.repositories.hosted_zones import ZoneRow
from app.schemas.hosted_zone import HostedZoneCreate, HostedZoneUpdate, Tag, VpcAssociation
from app.services.record_rules import RecordDraft, build_record

MAX_TAGS = 50
_RESERVED_TAG_PREFIX = "aws:"
_VPC_ID_RE = re.compile(r"^vpc-([0-9a-f]{8}|[0-9a-f]{17})$")


def list_zones(
    db: Session,
    user: User,
    *,
    search: str | None,
    zone_type: ZoneType | None,
    filters: Sequence[str],
    filter_mode: str,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[ZoneRow], int]:
    return zone_repository.list_zones(
        db,
        owner_id=user.id,
        search=search.strip() if search else None,
        zone_type=zone_type,
        filters=[parse_filter(raw) for raw in filters],
        filter_mode=filter_mode,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


def get_zone(db: Session, user: User, zone_id: str) -> ZoneRow:
    row = zone_repository.get_zone(db, owner_id=user.id, zone_id=zone_id)
    if row is None:
        raise NotFoundError(f"No hosted zone found with ID: {zone_id}", code="NoSuchHostedZone")
    return row


def _validated_vpcs(zone_type: ZoneType, vpcs: Sequence[VpcAssociation]) -> list[HostedZoneVpc]:
    if zone_type is ZoneType.PUBLIC:
        if vpcs:
            raise InvalidInputError(
                "VPCs can only be associated with private hosted zones", field="vpcs"
            )
        return []
    if not vpcs:
        raise InvalidInputError(
            "A private hosted zone must be associated with at least one VPC", field="vpcs"
        )
    seen: set[str] = set()
    for vpc in vpcs:
        if not _VPC_ID_RE.match(vpc.vpc_id):
            raise InvalidInputError(f"The VPC ID '{vpc.vpc_id}' is not valid", field="vpcs")
        if vpc.region not in AWS_REGIONS:
            raise InvalidInputError(f"The Region '{vpc.region}' is not valid", field="vpcs")
        if vpc.vpc_id in seen:
            raise InvalidInputError(
                f"The VPC '{vpc.vpc_id}' is listed more than once", field="vpcs"
            )
        seen.add(vpc.vpc_id)
    return [HostedZoneVpc(vpc_id=vpc.vpc_id, region=vpc.region) for vpc in vpcs]


def _validated_tags(tags: Sequence[Tag]) -> list[HostedZoneTag]:
    if len(tags) > MAX_TAGS:
        raise InvalidInputError(f"A hosted zone can have at most {MAX_TAGS} tags", field="tags")
    seen: set[str] = set()
    for tag in tags:
        if tag.key.lower().startswith(_RESERVED_TAG_PREFIX):
            raise InvalidInputError(
                f"Tag keys cannot start with '{_RESERVED_TAG_PREFIX}'", field="tags"
            )
        if tag.key in seen:
            raise InvalidInputError(
                f"The tag key '{tag.key}' is specified more than once", field="tags"
            )
        seen.add(tag.key)
    return [HostedZoneTag(key=tag.key, value=tag.value) for tag in tags]


def create_zone(
    db: Session, user: User, payload: HostedZoneCreate, *, max_zones: int = 0
) -> ZoneRow:
    """Create a zone together with the apex SOA and NS record sets Route 53 provides.

    ``max_zones`` is the account's quota of hosted zones; zero means no limit.
    """
    if max_zones and zone_repository.count_owned(db, user.id) >= max_zones:
        raise LimitExceededError(
            "This operation can't be completed because the current account has reached "
            f"the limit of {max_zones} hosted zones.",
            code="TooManyHostedZones",
        )
    try:
        name = normalize_zone_name(payload.name)
    except DnsNameError as exc:
        raise InvalidDomainNameError(str(exc), field="name") from None

    zone = HostedZone(
        id=new_hosted_zone_id(),
        owner_id=user.id,
        name=name,
        sort_key=sort_key(name),
        type=payload.type.value,
        description=payload.description.strip(),
        caller_reference=new_caller_reference(),
        vpcs=_validated_vpcs(payload.type, payload.vpcs),
        tags=_validated_tags(payload.tags),
    )
    name_servers = new_delegation_set(payload.type)
    zone.record_sets = [
        build_record(
            zone.id,
            RecordDraft(name=name, type=RecordType.NS, ttl=APEX_NS_TTL, values=tuple(name_servers)),
        ),
        build_record(
            zone.id,
            RecordDraft(
                name=name,
                type=RecordType.SOA,
                ttl=APEX_SOA_TTL,
                values=(soa_value(name_servers[0]),),
            ),
        ),
    ]
    db.add(zone)
    db.commit()
    return ZoneRow(zone, len(zone.record_sets), name_servers)


def _replace_tags(zone: HostedZone, tags: Sequence[HostedZoneTag]) -> None:
    """Make the zone's tags equal ``tags``, keeping the rows whose key stays."""
    replacements = {tag.key: tag for tag in tags}
    for existing in list(zone.tags):
        replacement = replacements.pop(existing.key, None)
        if replacement is None:
            zone.tags.remove(existing)
        else:
            existing.value = replacement.value
    zone.tags.extend(replacements.values())


def _replace_vpcs(zone: HostedZone, vpcs: Sequence[HostedZoneVpc]) -> None:
    """Make the zone's VPC associations equal ``vpcs``, keeping the rows whose VPC stays."""
    replacements = {vpc.vpc_id: vpc for vpc in vpcs}
    for existing in list(zone.vpcs):
        replacement = replacements.pop(existing.vpc_id, None)
        if replacement is None:
            zone.vpcs.remove(existing)
        else:
            existing.region = replacement.region
    zone.vpcs.extend(replacements.values())


def update_zone(db: Session, user: User, zone_id: str, changes: HostedZoneUpdate) -> ZoneRow:
    """Edit what can change after creation: the description, tags and VPC associations.

    Everything is validated before the zone is touched and saved in one transaction, so
    a rejected edit changes nothing.
    """
    row = get_zone(db, user, zone_id)
    zone = row.zone
    tags = None if changes.tags is None else _validated_tags(changes.tags)
    vpcs = None if changes.vpcs is None else _validated_vpcs(ZoneType(zone.type), changes.vpcs)

    if changes.description is not None:
        zone.description = changes.description.strip()
    if tags is not None:
        _replace_tags(zone, tags)
    if vpcs is not None:
        _replace_vpcs(zone, vpcs)
    zone.updated_at = utcnow()
    db.commit()
    db.refresh(zone, attribute_names=["tags", "vpcs"])
    return row


def delete_zone(db: Session, user: User, zone_id: str) -> None:
    zone = get_zone(db, user, zone_id).zone
    if record_repository.count_non_required(db, zone.id, zone.name):
        raise ConflictError(
            "The specified hosted zone contains non-required resource record sets "
            "and so cannot be deleted.",
            code="HostedZoneNotEmpty",
        )
    db.delete(zone)
    db.commit()


def replace_tags(db: Session, user: User, zone_id: str, tags: Sequence[Tag]) -> list[HostedZoneTag]:
    zone = get_zone(db, user, zone_id).zone
    _replace_tags(zone, _validated_tags(tags))
    db.commit()
    db.refresh(zone, attribute_names=["tags"])
    return zone.tags
