from typing import Annotated

from fastapi import APIRouter, Path

from app.dependencies import CurrentUser, DbSession, SettingsDep
from app.routers.responses import NOT_FOUND, UNAUTHORIZED
from app.schemas.record_set import ChangeInfo
from app.services import changes as change_service

router = APIRouter(prefix="/changes", tags=["Changes"], responses=UNAUTHORIZED)


@router.get(
    "/{change_id}",
    summary="Get the status of a change",
    description="Modelled on Route 53's `GetChange`. A change to a zone's records is "
    "`PENDING` for `R53_CHANGE_PROPAGATION_SECONDS` after it was saved and `INSYNC` from "
    "then on. The status is simulated: the records are final as soon as the change "
    "request returns, and nothing is propagated because no DNS is served. Changes older "
    "than a day are forgotten once their zone changes again.",
    responses=NOT_FOUND,
)
def get_change(
    change_id: Annotated[str, Path(description="Change ID", examples=["C2682N5HXP0BZ4"])],
    db: DbSession,
    user: CurrentUser,
    settings: SettingsDep,
) -> ChangeInfo:
    change = change_service.get_change(db, user, change_id)
    return ChangeInfo(
        id=change.id,
        status=change_service.status_of(change, settings),
        comment=change.comment,
        submitted_at=change.submitted_at,
    )
