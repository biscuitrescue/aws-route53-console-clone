"""Export a hosted zone (BIND or JSON) and import record sets from a BIND zone file."""

from typing import Any

from sqlalchemy.orm import Session

from app.domain.enums import ChangeAction, RecordType, RoutingPolicy, ZoneType
from app.domain.zonefile import ZoneFileRecord, parse_zone_file, render_zone_file
from app.errors import InvalidChangeBatchError, InvalidZoneFileError
from app.models import HostedZone, RecordSet
from app.models.base import utcnow
from app.repositories import records as record_repository
from app.repositories.hosted_zones import ZoneRow
from app.schemas.common import ErrorDetail
from app.schemas.record_set import Change, RecordSetInput
from app.schemas.transfer import (
    ImportedRecordSet,
    ImportSummary,
    ZoneFileImportRequest,
    ZoneFileImportResult,
)
from app.services import changes as change_service
from app.services.change_batch import apply_change_batch
from app.services.record_rules import describe, quota_message

_APEX_MANAGED_TYPES = frozenset({RecordType.SOA, RecordType.NS})


def _is_plain(record: RecordSet) -> bool:
    """Whether a record set can be expressed in a standard zone file."""
    return not record.is_alias and record.routing_policy == RoutingPolicy.SIMPLE


def export_bind(db: Session, row: ZoneRow) -> str:
    zone = row.zone
    records = record_repository.list_all(db, zone.id)
    comments = [
        f"Zone file for {zone.name} (hosted zone {zone.id})",
        f"Exported {utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}",
    ]
    comments.extend(
        f"Not exported (alias or routing policy record): {record.name} {record.type}"
        for record in records
        if not _is_plain(record)
    )
    return render_zone_file(
        zone.name,
        (
            ZoneFileRecord(
                record.name, RecordType(record.type), record.ttl or 0, tuple(record.values)
            )
            for record in records
            if _is_plain(record)
        ),
        comments,
    )


def _record_set_document(record: RecordSet) -> dict[str, Any]:
    """One record set in the shape of ``aws route53 list-resource-record-sets``."""
    document: dict[str, Any] = {"Name": record.name, "Type": record.type}
    if record.set_identifier:
        document["SetIdentifier"] = record.set_identifier
    if record.weight is not None:
        document["Weight"] = record.weight
    if record.region:
        document["Region"] = record.region
    if record.failover:
        document["Failover"] = record.failover
    if record.geo_continent_code or record.geo_country_code:
        location = {
            "ContinentCode": record.geo_continent_code,
            "CountryCode": record.geo_country_code,
            "SubdivisionCode": record.geo_subdivision_code,
        }
        document["GeoLocation"] = {key: value for key, value in location.items() if value}
    if record.routing_policy == RoutingPolicy.MULTIVALUE:
        document["MultiValueAnswer"] = True
    if record.health_check_id:
        document["HealthCheckId"] = record.health_check_id
    if record.is_alias:
        document["AliasTarget"] = {
            "HostedZoneId": record.alias_target_hosted_zone_id,
            "DNSName": record.alias_target_dns_name,
            "EvaluateTargetHealth": record.evaluate_target_health,
        }
    else:
        document["TTL"] = record.ttl
        document["ResourceRecords"] = [{"Value": value} for value in record.values]
    return document


def export_json(db: Session, row: ZoneRow) -> dict[str, Any]:
    """The zone and its record sets in the shape the AWS CLI returns."""
    zone = row.zone
    document: dict[str, Any] = {
        "HostedZone": {
            "Id": f"/hostedzone/{zone.id}",
            "Name": zone.name,
            "CallerReference": zone.caller_reference,
            "Config": {
                "Comment": zone.description,
                "PrivateZone": zone.type == ZoneType.PRIVATE,
            },
            "ResourceRecordSetCount": row.record_count,
        },
    }
    if zone.type == ZoneType.PRIVATE:
        document["VPCs"] = [{"VPCRegion": vpc.region, "VPCId": vpc.vpc_id} for vpc in zone.vpcs]
    else:
        document["DelegationSet"] = {
            "NameServers": [ns.removesuffix(".") for ns in row.name_servers]
        }
    document["Tags"] = [{"Key": tag.key, "Value": tag.value} for tag in zone.tags]
    document["ResourceRecordSets"] = [
        _record_set_document(record) for record in record_repository.list_all(db, zone.id)
    ]
    return document


def import_zone_file(
    db: Session, zone: HostedZone, request: ZoneFileImportRequest, *, max_records: int = 0
) -> ZoneFileImportResult:
    """Preview or apply a BIND zone file.

    The parsed record sets always run through the change batch so the preview reports
    the same rule violations an import would hit; a dry run then rolls back. Nothing is
    saved unless the whole file is clean.
    """
    parsed = parse_zone_file(request.content, zone.name)
    entries: list[ImportedRecordSet] = []
    changes: list[Change] = []
    change_entries: list[ImportedRecordSet] = []

    for record_set in parsed.record_sets:
        entry = ImportedRecordSet(
            line=record_set.line,
            name=record_set.name,
            type=record_set.type,
            ttl=record_set.ttl,
            values=record_set.values,
            status="create",
        )
        entries.append(entry)
        if record_set.name == zone.name and record_set.type in _APEX_MANAGED_TYPES:
            entry.status = "skip"
            entry.reason = (
                f"Route 53 manages the {record_set.type} record at the zone apex; "
                "the hosted zone keeps its own."
            )
            continue

        exists = record_repository.find_by_identity(
            db, zone.id, record_set.name, record_set.type, ""
        )
        if exists is not None and not request.replace_existing:
            entry.status = "error"
            entry.reason = (
                "Tried to create resource record set "
                f"{describe(record_set.name, record_set.type)} but it already exists"
            )
            continue
        if exists is not None:
            entry.status = "replace"
        changes.append(
            Change(
                action=ChangeAction.UPSERT if exists is not None else ChangeAction.CREATE,
                record_set=RecordSetInput(
                    name=record_set.name,
                    type=record_set.type,
                    ttl=record_set.ttl,
                    values=record_set.values,
                ),
            )
        )
        change_entries.append(entry)

    try:
        apply_change_batch(db, zone, changes)
    except InvalidChangeBatchError as exc:
        for failure in exc.details:
            failed = change_entries[failure["index"]]
            failed.status = "error"
            failed.reason = failure["message"]

    summary = ImportSummary()
    for entry in entries:
        setattr(summary, entry.status, getattr(summary, entry.status) + 1)
    syntax_errors = [ErrorDetail(line=issue.line, message=issue.message) for issue in parsed.issues]
    # Counted with the file's records applied, before the preview is rolled back.
    if max_records and record_repository.count_records(db, zone.id) > max_records:
        syntax_errors.append(ErrorDetail(message=quota_message(max_records)))
    has_errors = bool(syntax_errors) or summary.error > 0
    importable = summary.create + summary.replace

    change_id: str | None = None
    if request.dry_run or has_errors or not importable:
        db.rollback()
    if not request.dry_run:
        if has_errors:
            raise InvalidZoneFileError(
                "The zone file was not imported because it contains errors.",
                details=[
                    *(error.model_dump(exclude_none=True) for error in syntax_errors),
                    *(
                        {"line": entry.line, "message": entry.reason}
                        for entry in entries
                        if entry.status == "error"
                    ),
                ],
            )
        if not importable:
            raise InvalidZoneFileError("The zone file does not contain any records to import.")
        change_id = change_service.record(db, zone, "Zone file import").id
        db.commit()

    return ZoneFileImportResult(
        change_id=change_id,
        dry_run=request.dry_run,
        applied=not request.dry_run,
        summary=summary,
        record_sets=entries,
        errors=syntax_errors,
    )
