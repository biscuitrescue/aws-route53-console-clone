"""Use cases for record sets inside a hosted zone."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.enums import RecordType
from app.errors import NotFoundError
from app.models import HostedZone, RecordSet
from app.repositories import records as record_repository
from app.repositories.filtering import parse_filter
from app.schemas.record_set import Change, RecordSetInput, RecordSetOut, RecordSetUpdate
from app.services import record_rules
from app.services.change_batch import BatchOutcome, apply_change_batch

_INPUT_FIELDS = set(RecordSetInput.model_fields)


def list_records(
    db: Session,
    zone: HostedZone,
    *,
    search: str | None,
    types: Sequence[RecordType],
    filters: Sequence[str],
    filter_mode: str,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[RecordSet], int]:
    return record_repository.list_records(
        db,
        zone_id=zone.id,
        search=search.strip() if search else None,
        types=types,
        filters=[parse_filter(raw) for raw in filters],
        filter_mode=filter_mode,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


def get_record(db: Session, zone: HostedZone, record_id: str) -> RecordSet:
    record = record_repository.get_record(db, zone.id, record_id)
    if record is None:
        raise NotFoundError(
            f"No record found with ID {record_id} in hosted zone {zone.id}",
            code="NoSuchRecordSet",
        )
    return record


def create_record(db: Session, zone: HostedZone, payload: RecordSetInput) -> RecordSet:
    draft = record_rules.draft_record(zone.name, payload)
    record_rules.check_conflicts(db, zone, draft)
    record = record_rules.build_record(zone.id, draft)
    db.add(record)
    db.commit()
    return record


def _merge(record: RecordSet, changes: RecordSetUpdate) -> RecordSetInput:
    """Overlay a partial update on the stored record set."""
    current = RecordSetOut.from_model(record).model_dump(include=_INPUT_FIELDS)
    updates = changes.model_dump(exclude_unset=True)
    # Switching between alias and plain values replaces the other representation.
    if updates.get("alias_target") is not None and "values" not in updates:
        updates |= {"values": [], "ttl": None}
    elif updates.get("values") and "alias_target" not in updates:
        updates["alias_target"] = None
    return RecordSetInput.model_validate(current | updates)


def update_record(
    db: Session, zone: HostedZone, record_id: str, changes: RecordSetUpdate
) -> RecordSet:
    record = get_record(db, zone, record_id)
    draft = record_rules.draft_record(zone.name, _merge(record, changes))
    identity_changed = (draft.name, draft.type.value, draft.set_identifier) != (
        record.name,
        record.type,
        record.set_identifier,
    )
    if identity_changed:
        record_rules.ensure_not_required(zone.name, record)
    record_rules.check_conflicts(db, zone, draft, exclude_id=record.id)
    record_rules.apply_draft(record, draft)
    db.commit()
    return record


def delete_record(db: Session, zone: HostedZone, record_id: str) -> None:
    record = get_record(db, zone, record_id)
    record_rules.ensure_not_required(zone.name, record)
    db.delete(record)
    db.commit()


def apply_batch(db: Session, zone: HostedZone, changes: Sequence[Change]) -> BatchOutcome:
    outcome = apply_change_batch(db, zone, changes)
    db.commit()
    return outcome
