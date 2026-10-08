from fastapi import APIRouter, Response, status

from app.dependencies import CurrentSession, DbSession, SessionToken, SettingsDep
from app.errors import NotFoundError
from app.routers.responses import BAD_REQUEST, NOT_FOUND, UNAUTHORIZED
from app.schemas.auth import DemoCredentials, LoginRequest, SessionOut, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    summary="Sign in and start a session",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def login(
    payload: LoginRequest, response: Response, db: DbSession, settings: SettingsDep
) -> SessionOut:
    token, session = auth_service.login(db, settings, payload.email, payload.password)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return SessionOut(user=UserOut.model_validate(session.user), expires_at=session.expires_at)


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
def me(session: CurrentSession) -> SessionOut:
    return SessionOut(user=UserOut.model_validate(session.user), expires_at=session.expires_at)


@router.get(
    "/demo-credentials",
    summary="Credentials of the public demo account",
    description="Lets the sign-in page of a public demo show how to get in. Returns 404 when "
    "`R53_DEMO_CREDENTIALS_PUBLIC` is off.",
    responses=NOT_FOUND,
)
def demo_credentials(settings: SettingsDep) -> DemoCredentials:
    if not settings.demo_credentials_public:
        raise NotFoundError("Demo credentials are not published on this deployment.")
    return DemoCredentials(email=settings.demo_email, password=settings.demo_password)
