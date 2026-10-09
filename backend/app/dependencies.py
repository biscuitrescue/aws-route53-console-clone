"""FastAPI dependencies shared by the routers."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Path, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AuthSession, HostedZone, User
from app.repositories.hosted_zones import ZoneRow
from app.services import auth as auth_service
from app.services import hosted_zones as zone_service
from app.services.throttle import LoginThrottle


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSession = Annotated[Session, Depends(get_db)]


def get_login_throttle(request: Request) -> LoginThrottle:
    throttle: LoginThrottle = request.app.state.login_throttle
    return throttle


LoginThrottleDep = Annotated[LoginThrottle, Depends(get_login_throttle)]


def get_client_address(request: Request) -> str:
    """The address the request came from.

    Taken from the connection. Behind the reverse proxy, uvicorn replaces it with the
    address in ``X-Forwarded-For``, and only for proxies it was told to trust
    (``--forwarded-allow-ips``); the application never reads that header itself, so a
    client cannot choose its own identity.
    """
    return request.client.host if request.client else "unknown"


ClientAddress = Annotated[str, Depends(get_client_address)]


def get_session_token(request: Request, settings: SettingsDep) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


SessionToken = Annotated[str | None, Depends(get_session_token)]


def get_auth_session(db: DbSession, token: SessionToken) -> AuthSession:
    return auth_service.authenticate(db, token)


CurrentSession = Annotated[AuthSession, Depends(get_auth_session)]


def get_current_user(session: CurrentSession) -> User:
    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]

ZoneId = Annotated[str, Path(description="Hosted zone ID", examples=["Z0123456789ABCDEFGHIJ"])]


def get_zone_row(db: DbSession, user: CurrentUser, zone_id: ZoneId) -> ZoneRow:
    return zone_service.get_zone(db, user, zone_id)


CurrentZoneRow = Annotated[ZoneRow, Depends(get_zone_row)]


def get_zone(row: CurrentZoneRow) -> HostedZone:
    return row.zone


CurrentZone = Annotated[HostedZone, Depends(get_zone)]
