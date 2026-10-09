from fastapi import APIRouter, Response, status

from app.config import Settings
from app.dependencies import (
    ClientAddress,
    CurrentSession,
    DbSession,
    LoginThrottleDep,
    SandboxCreations,
    SandboxToken,
    SessionToken,
    SettingsDep,
)
from app.errors import NotFoundError, UnauthorizedError
from app.models import AuthSession
from app.routers.responses import BAD_REQUEST, NOT_FOUND, TOO_MANY_REQUESTS, UNAUTHORIZED
from app.schemas.auth import LoginRequest, PublishedCredentials, SessionOut, UserOut
from app.services import auth as auth_service
from app.services import sandbox as sandbox_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _session_out(session: AuthSession, settings: Settings) -> SessionOut:
    user = session.user
    return SessionOut(
        user=UserOut(
            id=user.id,
            # A sandbox is the visitor's own copy of the shared account and is shown as it.
            email=settings.demo_email.strip().lower() if user.is_sandbox else user.email,
            display_name=user.display_name,
            account_id=user.account_id,
        ),
        expires_at=session.expires_at,
    )


@router.post(
    "/login",
    summary="Sign in and start a session",
    description="Repeated failures from one address are throttled: the answer is then 429 "
    "with a `Retry-After` header, whether or not the account exists.\n\n"
    "With `R53_DEMO_SANDBOX` on, signing in to the demo account opens the caller's own "
    "sandbox, a private copy of the sample zones remembered by a second cookie.",
    responses={**UNAUTHORIZED, **BAD_REQUEST, **TOO_MANY_REQUESTS},
)
def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
    settings: SettingsDep,
    throttle: LoginThrottleDep,
    client: ClientAddress,
    sandbox_token: SandboxToken,
    sandbox_creations: SandboxCreations,
) -> SessionOut:
    throttle.check(client, payload.email)
    try:
        user = auth_service.verify_credentials(db, payload.email, payload.password)
    except UnauthorizedError:
        throttle.record_failure(client, payload.email)
        raise
    throttle.record_success(client, payload.email)

    if settings.demo_sandbox and user.email == settings.demo_email.strip().lower():
        user, new_sandbox_token = sandbox_service.open_sandbox(
            db, settings, user, sandbox_token, client=client, creations=sandbox_creations
        )
        if new_sandbox_token is not None:
            response.set_cookie(
                key=settings.sandbox_cookie_name,
                value=new_sandbox_token,
                max_age=settings.sandbox_ttl_seconds,
                httponly=True,
                samesite="lax",
                secure=settings.cookie_secure,
                path="/",
            )
    token, session = auth_service.open_session(db, settings, user)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return _session_out(session, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="End the current session")
def logout(response: Response, db: DbSession, token: SessionToken, settings: SettingsDep) -> None:
    auth_service.logout(db, token)
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.get("/me", summary="The signed-in user", responses=UNAUTHORIZED)
def me(session: CurrentSession, settings: SettingsDep) -> SessionOut:
    return _session_out(session, settings)


@router.get(
    "/published-credentials",
    summary="Credentials the sign-in page may show",
    description="Lets the sign-in page of a public deployment show how to get in. Returns 404 "
    "when `R53_DEMO_CREDENTIALS_PUBLIC` is off.",
    responses=NOT_FOUND,
)
def published_credentials(settings: SettingsDep) -> PublishedCredentials:
    if not settings.demo_credentials_public:
        raise NotFoundError("Credentials are not published on this deployment.")
    return PublishedCredentials(email=settings.demo_email, password=settings.demo_password)
