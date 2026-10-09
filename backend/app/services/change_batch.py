"""Atomic change batches, modelled on Route 53's ``ChangeResourceRecordSets``."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.domain.enums import ChangeAction
from app.errors import AppError, InvalidChangeBatchError
from app.models import HostedZone, RecordSet
from app.repositories import records as record_repository
from app.schemas.record_set import Change, RecordSetInput
from app.services import record_rules


@dataclass(slots=True)
class BatchOutcome:
    created: int = 0
    updated: int = 0
    deleted: int = 0
    record_sets: list[RecordSet] = field(default_factory=list)


def _delete(db: Session, zone: HostedZone, payload: RecordSetInput, outcome: BatchOutcome) -> None:
    name = record_rules.resolve_name(zone.name, payload.name)
    description = record_rules.describe(name, payload.type)
    record = record_repository.find_by_identity(
        db, zone.id, name, payload.type, (payload.set_identifier or "").strip()
    )
    if record is None:
        raise AppError(f"Tried to delete resource record set {description} but it was not found")

    submitted_values = sorted(value.strip() for value in payload.values if value.strip())
    values_differ = bool(submitted_values) and submitted_values != sorted(record.values)
    ttl_differs = payload.ttl is not None and payload.ttl != record.ttl
    if values_differ or ttl_differs:
        raise AppError(
            f"Tried to delete resource record set {description} but the values provided "
            "do not match the current values"
        )

    record_rules.ensure_not_required(zone.name, record)
    db.delete(record)
    db.flush()
    outcome.deleted += 1


def _save(
    db: Session, zone: HostedZone, payload: RecordSetInput, outcome: BatchOutcome, *, upsert: bool
) -> None:
    draft = record_rules.draft_record(zone.name, payload)
    existing = (
        record_repository.find_by_identity(
            db, zone.id, draft.name, draft.type, draft.set_identifier
        )
        if upsert
        else None
    )
    record_rules.check_conflicts(db, zone, draft, exclude_id=existing.id if existing else None)

    if existing is None:
        record = record_rules.build_record(zone.id, draft)
        db.add(record)
        outcome.created += 1
    else:
        record = existing
        record_rules.apply_draft(record, draft)
        outcome.updated += 1
    db.flush()
    record_rules.align_group_ttl(db, zone, draft, record.id)
    outcome.record_sets.append(record)


def apply_change_batch(db: Session, zone: HostedZone, changes: Sequence[Change]) -> BatchOutcome:
    """Apply every change or none of them.

    Changes run in order inside the caller's transaction, so later changes see earlier
    ones. Each change is validated before it touches the session; if any change fails
    the transaction is rolled back and all failures are reported together. The caller
    commits on success.
    """
    outcome = BatchOutcome()
    failures: list[dict[str, object]] = []
    for index, change in enumerate(changes):
        try:
            if change.action is ChangeAction.DELETE:
                _delete(db, zone, change.record_set, outcome)
            else:
                _save(
                    db,
                    zone,
                    change.record_set,
                    outcome,
                    upsert=change.action is ChangeAction.UPSERT,
                )
        except AppError as exc:
            failures.append({"index": index, "field": exc.field, "message": exc.message})

    if failures:
        db.rollback()
        messages = [str(failure["message"]) for failure in failures]
        summary = messages[0] if len(messages) == 1 else f"[{', '.join(messages)}]"
        raise InvalidChangeBatchError(summary, details=failures)
    return outcome
