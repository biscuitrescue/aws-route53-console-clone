"""Per-visitor sandboxes.

The demo account's password is public, so everyone signs in to the same account. With
sandboxes on, signing in to it does not open the account itself: each visitor gets a
private copy of the sample zones, found again through a long-lived cookie. A sandbox is
a row of ``users``, so the ownership check every zone query already makes is what keeps
visitors out of each other's data; nothing depends on the frontend.

The copies are made from the template, a user nobody can sign in as. Its zones are the
canonical seed and can never be edited, so no reset is ever needed.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.domain.enums import UserKind
from app.domain.identifiers import new_caller_reference, new_hosted_zone_id, new_record_id
from app.errors import TooManyRequestsError
from app.models import HostedZone, HostedZoneTag, HostedZoneVpc, RecordSet, RecordValue, User
from app.models.base import utcnow
from app.services.throttle import SlidingWindowCounter

TEMPLATE_EMAIL = "template@sandbox.invalid"
# Not an Argon2 hash, so no password verifies against it: these rows cannot sign in.
_NO_PASSWORD = "!"
_TOKEN_BYTES = 32
_COPIED_RECORD_COLUMNS = tuple(
    column.key
    for column in RecordSet.__table__.columns
    if column.key not in {"id", "zone_id", "created_at", "updated_at"}
)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_template(db: Session) -> User:
    """The owner of the canonical sample zones; created on first use."""
    template = db.scalar(select(User).where(User.kind == UserKind.TEMPLATE.value))
    if template is None:
        template = User(
            email=TEMPLATE_EMAIL,
            password_hash=_NO_PASSWORD,
            display_name="template",
            account_id="000000000000",
            kind=UserKind.TEMPLATE.value,
        )
        db.add(template)
        db.commit()
    return template


def copy_zones(db: Session, source: User, target: User) -> int:
    """Give ``target`` its own copy of every zone ``source`` owns; returns how many."""
    zones = db.scalars(
        select(HostedZone)
        .where(HostedZone.owner_id == source.id)
        .options(
            selectinload(HostedZone.vpcs),
            selectinload(HostedZone.tags),
            selectinload(HostedZone.record_sets),
        )
        .order_by(HostedZone.created_at, HostedZone.id)
    ).all()
    new_ids = {zone.id: new_hosted_zone_id() for zone in zones}
    for zone in zones:
        records = []
        for record in zone.record_sets:
            values = {key: getattr(record, key) for key in _COPIED_RECORD_COLUMNS}
            # An alias to a record of a copied zone has to follow it to the copy.
            target_zone = values["alias_target_hosted_zone_id"]
            values["alias_target_hosted_zone_id"] = new_ids.get(target_zone, target_zone)
            records.append(
                RecordSet(
                    id=new_record_id(),
                    zone_id=new_ids[zone.id],
                    value_rows=[
                        RecordValue(position=row.position, value=row.value)
                        for row in record.value_rows
                    ],
                    **values,
                )
            )
        db.add(
            HostedZone(
                id=new_ids[zone.id],
                owner_id=target.id,
                name=zone.name,
                sort_key=zone.sort_key,
                type=zone.type,
                description=zone.description,
                caller_reference=new_caller_reference(),
                created_by=zone.created_by,
                vpcs=[HostedZoneVpc(vpc_id=vpc.vpc_id, region=vpc.region) for vpc in zone.vpcs],
                tags=[HostedZoneTag(key=tag.key, value=tag.value) for tag in zone.tags],
                record_sets=records,
            )
        )
    return len(zones)


def purge(db: Session, settings: Settings, now: datetime, *, making_room_for: int = 0) -> int:
    """Delete sandboxes idle for too long, then the stalest beyond the cap.

    Their sessions, zones and records go with them through the foreign keys' cascades.
    Returns how many sandboxes were deleted.
    """
    is_sandbox = User.kind == UserKind.SANDBOX.value
    cutoff = now - timedelta(seconds=settings.sandbox_ttl_seconds)
    doomed = list(db.scalars(select(User.id).where(is_sandbox, User.last_seen_at < cutoff)))

    count = db.scalar(select(func.count(User.id)).where(is_sandbox)) or 0
    overflow = count - len(doomed) + making_room_for - settings.sandbox_max
    if overflow > 0:
        doomed += db.scalars(
            select(User.id)
            .where(is_sandbox, User.last_seen_at >= cutoff)
            .order_by(User.last_seen_at, User.id)
            .limit(overflow)
        )
    if doomed:
        db.execute(delete(User).where(User.id.in_(doomed)))
    return len(doomed)


def find(db: Session, token: str | None) -> User | None:
    """The sandbox a cookie token names, if it still exists."""
    if not token:
        return None
    return db.scalar(
        select(User).where(
            User.sandbox_key_hash == _hash_token(token), User.kind == UserKind.SANDBOX.value
        )
    )


def open_sandbox(
    db: Session,
    settings: Settings,
    account: User,
    token: str | None,
    *,
    client: str,
    creations: SlidingWindowCounter,
) -> tuple[User, str | None]:
    """Return the visitor's sandbox, starting a new one when the cookie names none.

    The second value is the token for a new sandbox cookie, or ``None`` when the
    visitor's existing one was found. Nothing is committed here: the caller opens the
    session in the same transaction, so a sandbox never exists half-made.
    """
    now = utcnow()
    existing = find(db, token)
    if existing is not None:
        existing.last_seen_at = now
        return existing, None

    wait = creations.retry_after(client)
    if wait > 0:
        raise TooManyRequestsError(
            "Too many new sessions were started from this address. Try again later.",
            retry_after=wait,
        )
    creations.add(client)

    purge(db, settings, now, making_room_for=1)
    new_token = secrets.token_urlsafe(_TOKEN_BYTES)
    key_hash = _hash_token(new_token)
    sandbox = User(
        # Never shown or signed in with; it only has to be unique.
        email=f"{key_hash[:32]}@sandbox.invalid",
        password_hash=_NO_PASSWORD,
        display_name=account.display_name,
        account_id=f"{secrets.randbelow(10**12):012d}",
        kind=UserKind.SANDBOX.value,
        sandbox_key_hash=key_hash,
        last_seen_at=now,
    )
    db.add(sandbox)
    db.flush()
    template = db.scalar(select(User).where(User.kind == UserKind.TEMPLATE.value))
    if template is not None:
        copy_zones(db, template, sandbox)
    return sandbox, new_token
