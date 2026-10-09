"""Sign-in throttling and the same-origin check on state-changing requests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.throttle import SlidingWindowCounter
from tests.conftest import API, PASSWORD, create_zone

LOGIN = f"{API}/auth/login"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(app: FastAPI) -> Clock:
    clock = Clock()
    app.state.login_throttle.set_clock(clock)
    return clock


def _attempt(client: TestClient, email: str, password: str = "wrong") -> int:
    return client.post(LOGIN, json={"email": email, "password": password}).status_code


# --- sign-in throttling ---------------------------------------------------------------


def test_repeated_failures_are_throttled_even_with_the_right_password(
    anonymous: TestClient, settings: Settings, clock: Clock
) -> None:
    for _ in range(settings.login_max_failures):
        assert _attempt(anonymous, settings.demo_email) == 401

    response = anonymous.post(LOGIN, json={"email": settings.demo_email, "password": PASSWORD})
    assert response.status_code == 429
    assert response.json() == {
        "code": "Throttling",
        "message": "Too many failed sign-in attempts. Wait a few minutes, then try again.",
        "details": [],
    }
    assert response.headers["retry-after"] == str(settings.login_failure_window_seconds)
    assert "set-cookie" not in response.headers


def test_the_limit_lifts_when_the_window_has_passed(
    anonymous: TestClient, settings: Settings, clock: Clock
) -> None:
    for _ in range(settings.login_max_failures):
        _attempt(anonymous, settings.demo_email)
        clock.now += 10
    assert _attempt(anonymous, settings.demo_email, PASSWORD) == 429

    # The first failure has now left the window, which makes room for one attempt.
    clock.now += settings.login_failure_window_seconds - 10 * settings.login_max_failures + 1
    assert _attempt(anonymous, settings.demo_email, PASSWORD) == 200


def test_an_unknown_account_is_throttled_exactly_like_a_real_one(
    anonymous: TestClient, settings: Settings, clock: Clock
) -> None:
    def statuses(email: str) -> list[int]:
        return [_attempt(anonymous, email) for _ in range(settings.login_max_failures + 2)]

    expected = [401] * settings.login_max_failures + [429, 429]
    assert statuses("nobody@example.com") == expected
    assert statuses("somebody-else@example.com") == expected


def test_a_successful_sign_in_clears_the_count(
    anonymous: TestClient, settings: Settings, clock: Clock
) -> None:
    for _ in range(3):
        for _ in range(settings.login_max_failures - 1):
            assert _attempt(anonymous, settings.demo_email) == 401
        assert _attempt(anonymous, settings.demo_email, PASSWORD) == 200


def test_one_client_cannot_lock_another_out(
    app: FastAPI, anonymous: TestClient, settings: Settings, clock: Clock
) -> None:
    for _ in range(settings.login_max_failures):
        _attempt(anonymous, settings.demo_email)
    assert _attempt(anonymous, settings.demo_email, PASSWORD) == 429

    with TestClient(app, client=("203.0.113.9", 40000)) as elsewhere:
        assert _attempt(elsewhere, settings.demo_email, PASSWORD) == 200


def test_a_forwarded_for_header_from_the_client_does_not_change_its_identity(
    anonymous: TestClient, settings: Settings, clock: Clock
) -> None:
    for _ in range(settings.login_max_failures):
        _attempt(anonymous, settings.demo_email)
    response = anonymous.post(
        LOGIN,
        json={"email": settings.demo_email, "password": PASSWORD},
        headers={"X-Forwarded-For": "198.51.100.7", "X-Real-IP": "198.51.100.7"},
    )
    assert response.status_code == 429


def test_trying_many_accounts_from_one_address_is_throttled(
    anonymous: TestClient, settings: Settings, clock: Clock
) -> None:
    for attempt in range(settings.login_max_failures_per_client):
        assert _attempt(anonymous, f"user{attempt}@example.com") == 401
    assert _attempt(anonymous, "one-more@example.com") == 429
    assert _attempt(anonymous, settings.demo_email, PASSWORD) == 429


def test_throttling_can_be_turned_off(settings: Settings) -> None:
    app = create_app(
        settings.model_copy(update={"login_max_failures": 0, "login_max_failures_per_client": 0})
    )
    with TestClient(app) as client:
        assert {_attempt(client, settings.demo_email) for _ in range(30)} == {401}
    app.state.engine.dispose()


def test_counter_reports_how_long_to_wait_and_forgets_old_events() -> None:
    clock = Clock()
    counter = SlidingWindowCounter(limit=2, window=60, clock=clock)
    assert counter.retry_after("a") == 0
    counter.add("a")
    clock.now += 20
    counter.add("a")
    assert counter.retry_after("a") == 40
    assert counter.retry_after("b") == 0
    clock.now += 40
    assert counter.retry_after("a") == 0
    counter.add("a")
    assert counter.retry_after("a") == 20
    counter.reset("a")
    assert counter.retry_after("a") == 0


# --- same-origin check ------------------------------------------------------------------


@pytest.mark.parametrize("fetch_site", ["cross-site", "same-site"])
def test_a_browser_request_from_another_origin_cannot_change_anything(
    client: TestClient, fetch_site: str
) -> None:
    zone = create_zone(client)
    headers = {"Sec-Fetch-Site": fetch_site, "Origin": "https://evil.example"}

    created = client.post(f"{API}/hostedzones", json={"name": "evil.com"}, headers=headers)
    deleted = client.delete(f"{API}/hostedzones/{zone['id']}", headers=headers)
    ended = client.post(f"{API}/auth/logout", headers=headers)

    for response in (created, deleted, ended):
        assert response.status_code == 403
        assert response.json()["code"] == "CrossOriginRequest"
    assert client.get(f"{API}/hostedzones").json()["total"] == 1
    assert client.get(f"{API}/auth/me").status_code == 200


def test_another_origin_cannot_sign_a_visitor_in(anonymous: TestClient, settings: Settings) -> None:
    response = anonymous.post(
        LOGIN,
        json={"email": settings.demo_email, "password": PASSWORD},
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert response.status_code == 403
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("fetch_site", ["same-origin", "none"])
def test_the_apps_own_pages_can_change_things(client: TestClient, fetch_site: str) -> None:
    response = client.post(
        f"{API}/hostedzones", json={"name": "mine.com"}, headers={"Sec-Fetch-Site": fetch_site}
    )
    assert response.status_code == 201


def test_reading_is_never_blocked(client: TestClient) -> None:
    response = client.get(f"{API}/hostedzones", headers={"Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        # Browsers without Sec-Fetch-Site: the Origin has to name the host addressed.
        ({"Origin": "https://evil.example"}, 403),
        ({"Origin": "null"}, 403),
        ({"Origin": "http://testserver"}, 201),
        # Behind the frontend's proxy the original host is in X-Forwarded-Host.
        ({"Origin": "https://console.example", "X-Forwarded-Host": "console.example"}, 201),
        ({"Origin": "https://evil.example", "X-Forwarded-Host": "console.example"}, 403),
        # Not a browser page at all (curl, scripts, these tests).
        ({}, 201),
    ],
)
def test_origin_is_checked_when_the_browser_sends_no_fetch_metadata(
    client: TestClient, headers: dict[str, str], status: int
) -> None:
    response = client.post(f"{API}/hostedzones", json={"name": "mine.com"}, headers=headers)
    assert response.status_code == status


def test_a_trusted_origin_is_let_through(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"trusted_origins": ["https://ui.example/"]}))
    with TestClient(app) as client:
        allowed = client.post(
            LOGIN,
            json={"email": settings.demo_email, "password": PASSWORD},
            headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://ui.example"},
        )
        refused = client.post(
            LOGIN,
            json={"email": settings.demo_email, "password": PASSWORD},
            headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://other.example"},
        )
    app.state.engine.dispose()
    assert allowed.status_code == 200
    assert refused.status_code == 403


def test_a_json_body_sent_as_a_plain_form_is_not_accepted(client: TestClient) -> None:
    """A cross-site form can post text/plain without a preflight; it must not parse as JSON."""
    response = client.post(
        f"{API}/hostedzones", content='{"name": "form.com"}', headers={"Content-Type": "text/plain"}
    )
    assert response.status_code == 422
    assert client.get(f"{API}/hostedzones").json()["total"] == 0
