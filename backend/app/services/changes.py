"""Change status, simulated.

Route 53 answers a record change with a change ID whose status is ``PENDING`` until
the change has reached every authoritative name server, then ``INSYNC``. Nothing is
propagated here, since no DNS is served; a change is simply reported as ``PENDING``
for a configured number of seconds after it was saved and ``INSYNC`` from then on.
The data itself is final the moment the request returns.
"""

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.enums import ChangeStatus
from app.domain.identifiers import new_change_id
from app.errors import NotFoundError
from app.models import Change, HostedZone, User
from app.models.base import utcnow

# Old changes are dropped when a zone gets a new one; long before this they are INSYNC.
_RETENTION = timedelta(days=1)


def record(db: Session, zone: HostedZone, comment: str = "") -> Change:
    """Note a change in the caller's transaction; the caller commits."""
    now = utcnow()
    db.execute(
        delete(Change).where(Change.zone_id == zone.id, Change.submitted_at < now - _RETENTION)
    )
    change = Change(id=new_change_id(), zone_id=zone.id, comment=comment, submitted_at=now)
    db.add(change)
    return change


def status_of(change: Change, settings: Settings, now: datetime | None = None) -> ChangeStatus:
    elapsed = (now or utcnow()) - change.submitted_at
    if elapsed >= timedelta(seconds=settings.change_propagation_seconds):
        return ChangeStatus.INSYNC
    return ChangeStatus.PENDING


def get_change(db: Session, user: User, change_id: str) -> Change:
    """A change to one of the user's zones; anyone else's does not exist for them."""
    change = db.scalar(
        select(Change)
        .join(HostedZone, HostedZone.id == Change.zone_id)
        .where(Change.id == change_id, HostedZone.owner_id == user.id)
    )
    if change is None:
        raise NotFoundError(f"No change found with ID: {change_id}", code="NoSuchChange")
    return change
