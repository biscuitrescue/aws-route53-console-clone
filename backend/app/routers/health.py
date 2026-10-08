from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.dependencies import DbSession

router = APIRouter(tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    database: str


@router.get("/health", summary="Liveness and database check")
def health(db: DbSession) -> HealthStatus:
    db.execute(text("SELECT 1"))
    return HealthStatus(status="ok", database="ok")
