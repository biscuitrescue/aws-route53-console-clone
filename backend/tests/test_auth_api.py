from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.models import AuthSession, User
from app.models.base import utcnow
from tests.conftest import API, PASSWORD


def _login(client: TestClient, settings: Settings, password: str = PASSWORD) -> Response:
    return client.post(
        f"{API}/auth/login", json={"email": settings.demo_email, "password": password}
    )


def test_health_needs_no_session(anonymous: TestClient) -> None:
    response = anonymous.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_login_sets_a_hardened_session_cookie(anonymous: TestClient, settings: Settings) -> None:
    response = anonymous.post(
        f"{API}/auth/login", json={"email": settings.demo_email.upper(), "password": PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": 1,
        "email": settings.demo_email,
        "display_name": settings.demo_display_name,
        "account_id": settings.demo_account_id,
    }

    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{settings.session_cookie_name}=")
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert f"max-age={settings.session_ttl_seconds}" in cookie
    assert "secure" not in cookie


def test_cookie_is_secure_in_production(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"cookie_secure": True}))
    with TestClient(app, base_url="https://testserver") as client:
        response = _login(client, settings)
    app.state.engine.dispose()
    assert "secure" in response.headers["set-cookie"].lower()


def test_wrong_password_and_unknown_user_fail_the_same_way(
    anonymous: TestClient, settings: Settings
) -> None:
    wrong_password = anonymous.post(
        f"{API}/auth/login", json={"email": settings.demo_email, "password": "nope"}
    )
    unknown_user = anonymous.post(
        f"{API}/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    for response in (wrong_password, unknown_user):
        assert response.status_code == 401
        assert response.json() == {
            "code": "AuthFailure",
            "message": "Your authentication information is incorrect. Please try again.",
            "details": [],
        }
        assert "set-cookie" not in response.headers


def test_a_hash_with_older_parameters_is_upgraded_at_sign_in(
    anonymous: TestClient, settings: Settings, db: Session
) -> None:
    from argon2 import PasswordHasher

    user = db.scalars(select(User)).one()
    user.password_hash = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4).hash(
        PASSWORD
    )
    db.commit()

    assert _login(anonymous, settings).status_code == 200
    db.refresh(user)
    assert "$m=19456,t=2,p=1$" in user.password_hash
    # The new hash still verifies, and a wrong password still does not.
    assert _login(anonymous, settings).status_code == 200
    assert _login(anonymous, settings, "nope").status_code == 401


def test_me_returns_the_session_user(client: TestClient, settings: Settings) -> None:
    response = client.get(f"{API}/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == settings.demo_email


def test_protected_routes_require_a_session(anonymous: TestClient) -> None:
    for path in ("/auth/me", "/hostedzones", "/hostedzones/Z1", "/hostedzones/Z1/records"):
        response = anonymous.get(f"{API}{path}")
        assert response.status_code == 401, path
        assert response.json()["code"] == "Unauthorized"


def test_a_forged_token_is_rejected(anonymous: TestClient, settings: Settings) -> None:
    anonymous.cookies.set(settings.session_cookie_name, "not-a-real-token")
    assert anonymous.get(f"{API}/auth/me").status_code == 401


def test_logout_ends_the_session_and_clears_the_cookie(
    client: TestClient, settings: Settings, db: Session
) -> None:
    token = client.cookies.get(settings.session_cookie_name)
    response = client.post(f"{API}/auth/logout")
    assert response.status_code == 204
    assert f"{settings.session_cookie_name}=" in response.headers["set-cookie"]
    assert db.scalars(select(AuthSession)).all() == []

    # Replaying the old token no longer works.
    client.cookies.set(settings.session_cookie_name, token or "")
    assert client.get(f"{API}/auth/me").status_code == 401


def test_logout_without_a_session_is_harmless(anonymous: TestClient) -> None:
    assert anonymous.post(f"{API}/auth/logout").status_code == 204


def test_only_a_hash_of_the_token_is_stored(
    client: TestClient, settings: Settings, db: Session
) -> None:
    token = client.cookies.get(settings.session_cookie_name)
    stored = db.scalars(select(AuthSession)).one()
    assert token
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_expired_sessions_are_rejected_then_purged_on_login(
    client: TestClient, settings: Settings, db: Session
) -> None:
    session = db.scalars(select(AuthSession)).one()
    session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    response = client.get(f"{API}/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "SessionExpired"

    assert _login(client, settings).status_code == 200
    remaining = db.scalars(select(AuthSession)).all()
    assert len(remaining) == 1
    assert remaining[0].expires_at > utcnow()


def test_a_session_survives_an_application_restart(
    client: TestClient, settings: Settings, app: FastAPI
) -> None:
    token = client.cookies.get(settings.session_cookie_name)
    restarted = create_app(settings)
    with TestClient(restarted) as fresh_client:
        fresh_client.cookies.set(settings.session_cookie_name, token or "")
        assert fresh_client.get(f"{API}/auth/me").status_code == 200
    restarted.state.engine.dispose()


def test_malformed_login_body_uses_the_common_error_shape(anonymous: TestClient) -> None:
    response = anonymous.post(f"{API}/auth/login", json={"email": "demo@example.com"})
    assert response.status_code == 422
    assert response.json() == {
        "code": "ValidationError",
        "message": "The request is not valid.",
        "details": [{"field": "password", "message": "Field required"}],
    }


def test_unknown_routes_use_the_common_error_shape(anonymous: TestClient) -> None:
    response = anonymous.get(f"{API}/nope")
    assert response.status_code == 404
    assert response.json() == {"code": "NotFound", "message": "Not Found", "details": []}


def test_docs_are_served(anonymous: TestClient) -> None:
    assert anonymous.get("/docs", follow_redirects=False).headers["location"] == "/api/docs"
    assert anonymous.get("/api/docs").status_code == 200
    schema = anonymous.get("/api/openapi.json").json()
    assert "/api/v1/hostedzones/{zone_id}/records:batch" in schema["paths"]


def test_credentials_are_published_by_default(anonymous: TestClient, settings: Settings) -> None:
    response = anonymous.get(f"{API}/auth/published-credentials")
    assert response.status_code == 200
    assert response.json() == {"email": settings.demo_email, "password": PASSWORD}


def test_published_credentials_can_be_withheld(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"demo_credentials_public": False}))
    with TestClient(app) as client:
        response = client.get(f"{API}/auth/published-credentials")
    app.state.engine.dispose()
    assert response.status_code == 404
    assert response.json()["code"] == "NotFound"
