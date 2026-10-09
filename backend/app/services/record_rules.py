"""Route 53's rules for a single record set: shape, routing policy and conflicts."""

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.aws_regions import AWS_REGIONS
from app.domain.dns_names import (
    DnsNameError,
    is_wildcard,
    normalize_record_name,
    sort_key,
    validate_hostname,
)
from app.domain.enums import FailoverRole, RecordType, RoutingPolicy
from app.domain.identifiers import new_record_id
from app.domain.record_validation import MAX_TTL, RecordValueError, validate_values
from app.errors import AppError, ConflictError, InvalidInputError, LimitExceededError
from app.models import HostedZone, RecordSet
from app.repositories import records as record_repository
from app.schemas.record_set import RecordSetInput

_SIMPLE_ONLY_TYPES = frozenset({RecordType.NS, RecordType.SOA})
_NO_ALIAS_TYPES = frozenset({RecordType.NS, RecordType.SOA})
_NO_MULTIVALUE_TYPES = frozenset({RecordType.CNAME, RecordType.NS, RecordType.SOA})
_MAX_WEIGHT = 255
_CONTINENT_CODES = frozenset({"AF", "AN", "AS", "EU", "NA", "OC", "SA"})
# A country is two letters; "*" is the default location that catches everything else.
_COUNTRY_CODE_RE = re.compile(r"^([A-Z]{2}|\*)$")


@dataclass(slots=True)
class RecordDraft:
    """A validated, normalised record set that is ready to be stored."""

    name: str
    type: RecordType
    ttl: int | None = None
    values: tuple[str, ...] = ()
    routing_policy: RoutingPolicy = RoutingPolicy.SIMPLE
    set_identifier: str = ""
    weight: int | None = None
    region: str | None = None
    failover: FailoverRole | None = None
    geo_continent_code: str | None = None
    geo_country_code: str | None = None
    geo_subdivision_code: str | None = None
    health_check_id: str | None = None
    alias_dns_name: str | None = None
    alias_hosted_zone_id: str | None = None
    evaluate_target_health: bool = False

    @property
    def is_alias(self) -> bool:
        return self.alias_dns_name is not None


def describe(name: str, record_type: str) -> str:
    return f"[name='{name}', type='{record_type}']"


def resolve_name(zone_name: str, raw_name: str) -> str:
    try:
        return normalize_record_name(raw_name, zone_name)
    except DnsNameError as exc:
        raise InvalidInputError(str(exc), field="name") from None


def _apply_routing(draft: RecordDraft, payload: RecordSetInput) -> None:
    policy = payload.routing_policy
    if policy is RoutingPolicy.SIMPLE:
        return
    if draft.type in _SIMPLE_ONLY_TYPES:
        raise InvalidInputError(
            f"{draft.type} records support only the simple routing policy",
            field="routing_policy",
        )

    identifier = (payload.set_identifier or "").strip()
    if not identifier:
        raise InvalidInputError(
            "A record ID is required for this routing policy", field="set_identifier"
        )
    draft.routing_policy = policy
    draft.set_identifier = identifier
    draft.health_check_id = (payload.health_check_id or "").strip() or None

    match policy:
        case RoutingPolicy.WEIGHTED:
            if payload.weight is None or not 0 <= payload.weight <= _MAX_WEIGHT:
                raise InvalidInputError(
                    f"Weight must be a whole number between 0 and {_MAX_WEIGHT}", field="weight"
                )
            draft.weight = payload.weight
        case RoutingPolicy.LATENCY:
            if payload.region not in AWS_REGIONS:
                raise InvalidInputError("Choose a valid AWS Region", field="region")
            draft.region = payload.region
        case RoutingPolicy.FAILOVER:
            if payload.failover is None:
                raise InvalidInputError(
                    "Choose a failover record type: Primary or Secondary", field="failover"
                )
            draft.failover = payload.failover
        case RoutingPolicy.GEOLOCATION:
            location = payload.geolocation
            continent = (location.continent_code or "").upper() if location else ""
            country = (location.country_code or "").upper() if location else ""
            subdivision = (location.subdivision_code or "").upper() if location else ""
            if not continent and not country:
                raise InvalidInputError("Choose a location", field="geolocation")
            if continent and country:
                raise InvalidInputError(
                    "Specify either a continent or a country, not both", field="geolocation"
                )
            if continent and continent not in _CONTINENT_CODES:
                raise InvalidInputError(
                    f"'{continent}' is not a valid continent code", field="geolocation"
                )
            if country and not _COUNTRY_CODE_RE.match(country):
                raise InvalidInputError(
                    f"'{country}' is not a valid country code", field="geolocation"
                )
            if subdivision and not country:
                raise InvalidInputError("A subdivision requires a country", field="geolocation")
            draft.geo_continent_code = continent or None
            draft.geo_country_code = country or None
            draft.geo_subdivision_code = subdivision or None
        case RoutingPolicy.MULTIVALUE:
            if draft.type in _NO_MULTIVALUE_TYPES:
                raise InvalidInputError(
                    f"{draft.type} records do not support multivalue answer routing",
                    field="routing_policy",
                )
            if draft.is_alias:
                raise InvalidInputError(
                    "Alias records do not support multivalue answer routing",
                    field="routing_policy",
                )
            if len(draft.values) != 1:
                raise InvalidInputError(
                    "Multivalue answer records must have exactly one value", field="values"
                )


def draft_record(zone_name: str, payload: RecordSetInput) -> RecordDraft:
    """Validate a record set against the rules that need no database access."""
    name = resolve_name(zone_name, payload.name)
    record_type = payload.type
    if record_type is RecordType.SOA and name != zone_name:
        raise InvalidInputError("SOA records are only permitted at the zone apex", field="type")
    if record_type is RecordType.CNAME and name == zone_name:
        raise InvalidInputError(
            f"RRSet of type CNAME with DNS name {name} is not permitted at apex "
            f"in zone {zone_name}",
            field="type",
        )

    if record_type is RecordType.DS and name == zone_name:
        # A zone's own DS record belongs in its parent zone.
        raise InvalidInputError(
            f"RRSet of type DS with DNS name {name} is not permitted at apex in zone {zone_name}",
            field="type",
        )

    if record_type is RecordType.NS and is_wildcard(name):
        raise InvalidInputError("NS records cannot have a wildcard name", field="name")

    draft = RecordDraft(name=name, type=record_type)
    if payload.alias_target is not None:
        if record_type in _NO_ALIAS_TYPES:
            raise InvalidInputError(
                f"{record_type} records cannot be alias records", field="alias_target"
            )
        if any(value.strip() for value in payload.values):
            raise InvalidInputError("Alias records cannot have values", field="values")
        target = payload.alias_target.dns_name.strip().lower()
        try:
            validate_hostname(target)
        except DnsNameError as exc:
            raise InvalidInputError(str(exc), field="alias_target") from None
        draft.alias_dns_name = target if target.endswith(".") else f"{target}."
        draft.alias_hosted_zone_id = payload.alias_target.hosted_zone_id.strip()
        draft.evaluate_target_health = payload.alias_target.evaluate_target_health
    else:
        if payload.ttl is None:
            raise InvalidInputError("TTL is required", field="ttl")
        if not 0 <= payload.ttl <= MAX_TTL:
            raise InvalidInputError(f"TTL must be between 0 and {MAX_TTL}", field="ttl")
        draft.ttl = payload.ttl
        try:
            draft.values = tuple(validate_values(record_type, payload.values))
        except RecordValueError as exc:
            raise InvalidInputError(str(exc), field="values") from None

    _apply_routing(draft, payload)
    return draft


def check_conflicts(
    db: Session, zone: HostedZone, draft: RecordDraft, *, exclude_id: str | None = None
) -> None:
    """Reject a draft that clashes with record sets already at the same name."""
    siblings = [
        record
        for record in record_repository.list_at_name(db, zone.id, draft.name)
        if record.id != exclude_id
    ]
    for sibling in siblings:
        same_type = sibling.type == draft.type
        if same_type and sibling.set_identifier == draft.set_identifier:
            raise ConflictError(
                f"Tried to create resource record set {describe(draft.name, draft.type)} "
                "but it already exists",
                code="RecordSetAlreadyExists",
                field="name",
            )
        if draft.type is RecordType.CNAME and not same_type:
            raise ConflictError(
                f"RRSet of type CNAME with DNS name {draft.name} is not permitted as it "
                f"conflicts with other records with the same DNS name in zone {zone.name}",
                code="RecordSetConflict",
                field="type",
            )
        if sibling.type == RecordType.CNAME and not same_type:
            raise ConflictError(
                f"RRSet of type {draft.type} with DNS name {draft.name} is not permitted "
                "because a conflicting RRSet of type CNAME with the same DNS name already "
                f"exists in zone {zone.name}",
                code="RecordSetConflict",
                field="type",
            )
        if same_type and sibling.routing_policy != draft.routing_policy:
            raise ConflictError(
                f"RRSet with DNS name {draft.name} and type {draft.type} cannot use the "
                f"{draft.routing_policy} routing policy because a record with the same name "
                f"and type uses the {sibling.routing_policy} routing policy",
                code="RecordSetConflict",
                field="routing_policy",
            )
        if same_type and draft.region is not None and sibling.region == draft.region:
            raise ConflictError(
                f"RRSet with DNS name {draft.name} and type {draft.type} already has a "
                f"latency record for the Region {draft.region}",
                code="RecordSetConflict",
                field="region",
            )
        if same_type and _same_location(draft, sibling):
            raise ConflictError(
                f"RRSet with DNS name {draft.name} and type {draft.type} already has a "
                "geolocation record for this location",
                code="RecordSetConflict",
                field="geolocation",
            )
        if same_type and draft.failover is not None and sibling.failover == draft.failover:
            raise ConflictError(
                f"RRSet with DNS name {draft.name} and type {draft.type} already has a "
                f"{draft.failover.lower()} failover record",
                code="RecordSetConflict",
                field="failover",
            )


def _same_location(draft: RecordDraft, record: RecordSet) -> bool:
    if draft.routing_policy is not RoutingPolicy.GEOLOCATION:
        return False
    return (draft.geo_continent_code, draft.geo_country_code, draft.geo_subdivision_code) == (
        record.geo_continent_code,
        record.geo_country_code,
        record.geo_subdivision_code,
    )


def align_group_ttl(db: Session, zone: HostedZone, draft: RecordDraft, record_id: str) -> None:
    """Give every record of a routed group the TTL of the one just saved.

    Records that share a name, type and routing policy are answered as one group, and
    Route 53 changes all of their TTLs to the last value specified.
    """
    if draft.routing_policy is RoutingPolicy.SIMPLE or draft.ttl is None:
        return
    for sibling in record_repository.list_at_name(db, zone.id, draft.name):
        in_group = sibling.type == draft.type and sibling.routing_policy == draft.routing_policy
        if in_group and sibling.id != record_id and not sibling.is_alias:
            sibling.ttl = draft.ttl


def ensure_within_quota(db: Session, zone: HostedZone, max_records: int) -> None:
    """Refuse changes that leave the zone with more records than its quota allows.

    Called after the changes are flushed and before they are committed, so the count
    includes them and raising discards them. Zero means no limit.
    """
    if max_records and record_repository.count_records(db, zone.id) > max_records:
        raise LimitExceededError(quota_message(max_records))


def quota_message(max_records: int) -> str:
    return (
        "This operation can't be completed because the hosted zone would exceed the "
        f"limit of {max_records} records."
    )


def ensure_not_required(zone_name: str, record: RecordSet) -> None:
    """The apex SOA and NS record sets belong to the zone and cannot be removed."""
    if record.name != zone_name:
        return
    if record.type == RecordType.SOA:
        raise AppError(
            "A HostedZone must contain exactly one SOA record", code="InvalidChangeBatch"
        )
    if record.type == RecordType.NS:
        raise AppError(
            "A HostedZone must contain at least one NS record for the zone itself.",
            code="InvalidChangeBatch",
        )


def apply_draft(record: RecordSet, draft: RecordDraft) -> None:
    record.name = draft.name
    record.sort_key = sort_key(draft.name)
    record.type = draft.type.value
    record.ttl = draft.ttl
    record.routing_policy = draft.routing_policy.value
    record.set_identifier = draft.set_identifier
    record.weight = draft.weight
    record.region = draft.region
    record.failover = draft.failover.value if draft.failover else None
    record.geo_continent_code = draft.geo_continent_code
    record.geo_country_code = draft.geo_country_code
    record.geo_subdivision_code = draft.geo_subdivision_code
    record.health_check_id = draft.health_check_id
    record.is_alias = draft.is_alias
    record.alias_target_dns_name = draft.alias_dns_name
    record.alias_target_hosted_zone_id = draft.alias_hosted_zone_id
    record.evaluate_target_health = draft.evaluate_target_health
    record.set_values(list(draft.values))


def build_record(zone_id: str, draft: RecordDraft) -> RecordSet:
    record = RecordSet(id=new_record_id(), zone_id=zone_id)
    apply_draft(record, draft)
    return record
