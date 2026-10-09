"""Per-visitor sandboxes: isolation, persistence, cleanup and quotas."""

from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.enums import UserKind
from app.main import create_app
from app.models import AuthSession, HostedZone, RecordSet, User
from app.models.base import utcnow
from app.seed import seed
from tests.conftest import API, PASSWORD, create_record, create_zone

SEEDED_ZONES = 12


@pytest.fixture
def settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"demo_sandbox": True, "seed_demo_data": True})


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    with application.state.session_factory() as session:
        seed(session, settings)
    yield application
    application.state.engine.dispose()


def _sign_in(client: TestClient, settings: Settings) -> dict[str, object]:
    response = client.post(
        f"{API}/auth/login", json={"email": settings.demo_email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    user: dict[str, object] = response.json()["user"]
    return user


@pytest.fixture
def visitor(app: FastAPI, settings: Settings) -> Iterator[TestClient]:
    with TestClient(app) as client:
        _sign_in(client, settings)
        yield client


@pytest.fixture
def other_visitor(app: FastAPI, settings: Settings) -> Iterator[TestClient]:
    with TestClient(app) as client:
        _sign_in(client, settings)
        yield client


def _zones(client: TestClient) -> list[dict[str, object]]:
    items: list[dict[str, object]] = client.get(f"{API}/hostedzones?page_size=500").json()["items"]
    return items


def _sandboxes(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.kind == UserKind.SANDBOX.value)))


# --- every visitor gets their own copy --------------------------------------------------


def test_each_visitor_starts_with_their_own_copy_of_the_sample_zones(
    visitor: TestClient, other_visitor: TestClient
) -> None:
    mine, theirs = _zones(visitor), _zones(other_visitor)
    assert len(mine) == len(theirs) == SEEDED_ZONES
    assert [zone["name"] for zone in mine] == [zone["name"] for zone in theirs]
    assert {zone["record_count"] for zone in mine} == {zone["record_count"] for zone in theirs}
    assert not {zone["id"] for zone in mine} & {zone["id"] for zone in theirs}


def test_a_copy_is_complete(visitor: TestClient, db: Session) -> None:
    template = db.scalars(select(User).where(User.kind == UserKind.TEMPLATE.value)).one()
    sandbox = _sandboxes(db)[0]

    def snapshot(owner: User) -> list[tuple[object, ...]]:
        zones = db.scalars(select(HostedZone).where(HostedZone.owner_id == owner.id)).all()
        return sorted(
            (
                zone.name,
                zone.type,
                zone.description,
                tuple((tag.key, tag.value) for tag in zone.tags),
                tuple((vpc.vpc_id, vpc.region) for vpc in zone.vpcs),
                tuple(
                    sorted(
                        (
                            record.name,
                            record.type,
                            record.ttl,
                            record.routing_policy,
                            record.set_identifier,
                            record.weight,
                            record.is_alias,
                            record.alias_target_dns_name,
                            tuple(record.values),
                        )
                        for record in zone.record_sets
                    )
                ),
            )
            for zone in zones
        )

    assert snapshot(sandbox) == snapshot(template)


def test_the_visitor_is_shown_as_the_demo_account(visitor: TestClient, settings: Settings) -> None:
    user = visitor.get(f"{API}/auth/me").json()["user"]
    assert user["email"] == settings.demo_email
    assert user["display_name"] == settings.demo_display_name
    assert len(user["account_id"]) == 12
    assert user["account_id"].isdigit()


def test_sandbox_cookie_is_hardened_and_only_its_hash_is_stored(
    app: FastAPI, settings: Settings, db: Session
) -> None:
    with TestClient(app) as client:
        response = client.post(
            f"{API}/auth/login", json={"email": settings.demo_email, "password": PASSWORD}
        )
        token = client.cookies.get(settings.sandbox_cookie_name)
    cookies = [
        value.lower()
        for name, value in response.headers.multi_items()
        if name == "set-cookie" and value.startswith(settings.sandbox_cookie_name)
    ]
    assert len(cookies) == 1
    assert "httponly" in cookies[0]
    assert "samesite=lax" in cookies[0]
    assert f"max-age={settings.sandbox_ttl_seconds}" in cookies[0]
    stored = _sandboxes(db)[0]
    assert token
    assert stored.sandbox_key_hash != token
    assert len(stored.sandbox_key_hash or "") == 64


# --- isolation, enforced by the backend -------------------------------------------------


def test_destruction_by_one_visitor_does_not_reach_another(
    visitor: TestClient, other_visitor: TestClient
) -> None:
    before = _zones(other_visitor)
    for zone in _zones(visitor):
        records = visitor.get(f"{API}/hostedzones/{zone['id']}/records?page_size=500").json()
        removable = [
            {
                "action": "DELETE",
                "record_set": {
                    "name": record["name"],
                    "type": record["type"],
                    "set_identifier": record["set_identifier"],
                },
            }
            for record in records["items"]
            if not (record["name"] == zone["name"] and record["type"] in ("NS", "SOA"))
        ]
        if removable:
            batch = visitor.post(
                f"{API}/hostedzones/{zone['id']}/records:batch", json={"changes": removable}
            )
            assert batch.status_code == 200, batch.text
        assert visitor.delete(f"{API}/hostedzones/{zone['id']}").status_code == 204

    assert _zones(visitor) == []
    assert _zones(other_visitor) == before


def test_a_visitor_cannot_read_or_change_another_visitors_zone(
    visitor: TestClient, other_visitor: TestClient
) -> None:
    zone_id = _zones(other_visitor)[0]["id"]
    record = other_visitor.get(f"{API}/hostedzones/{zone_id}/records").json()["items"][0]
    base = f"{API}/hostedzones/{zone_id}"
    change = {"action": "CREATE", "record_set": {"name": "x", "type": "A", "ttl": 60}}

    attempts = [
        visitor.get(base),
        visitor.patch(base, json={"description": "taken over"}),
        visitor.delete(base),
        visitor.get(f"{base}/tags"),
        visitor.put(f"{base}/tags", json={"tags": [{"key": "owned", "value": "yes"}]}),
        visitor.get(f"{base}/records"),
        visitor.post(
            f"{base}/records", json={"name": "x", "type": "A", "ttl": 60, "values": ["192.0.2.9"]}
        ),
        visitor.post(f"{base}/records:batch", json={"changes": [change]}),
        visitor.get(f"{base}/records/{record['id']}"),
        visitor.patch(f"{base}/records/{record['id']}", json={"ttl": 1}),
        visitor.delete(f"{base}/records/{record['id']}"),
        visitor.get(f"{base}/export?format=json"),
        visitor.post(f"{base}/import", json={"content": "x 60 IN A 192.0.2.9\n", "dry_run": False}),
    ]
    for response in attempts:
        assert response.status_code == 404, response.request.url
        assert response.json()["code"] == "NoSuchHostedZone"

    assert other_visitor.get(base).json()["description"] != "taken over"
    assert other_visitor.get(f"{base}/records/{record['id']}").json() == record


def test_another_visitors_zones_never_show_up_in_lists_or_search(
    visitor: TestClient, other_visitor: TestClient
) -> None:
    create_zone(other_visitor, "only-theirs.com", description="private")
    assert visitor.get(f"{API}/hostedzones?search=only-theirs").json()["total"] == 0
    assert visitor.get(f"{API}/hostedzones?filter=name:contains:only-theirs").json()["total"] == 0
    assert other_visitor.get(f"{API}/hostedzones?search=only-theirs").json()["total"] == 1


def test_nobody_can_sign_in_as_a_sandbox_or_the_template(
    visitor: TestClient, app: FastAPI, db: Session
) -> None:
    hidden = db.scalars(select(User).where(User.kind != UserKind.ACCOUNT.value)).all()
    assert {user.kind for user in hidden} == {"sandbox", "template"}
    with TestClient(app) as stranger:
        for user in hidden:
            for password in ("!", "", PASSWORD):
                response = stranger.post(
                    f"{API}/auth/login", json={"email": user.email, "password": password or "x"}
                )
                assert response.status_code == 401


def test_the_template_is_untouched_by_anything_a_visitor_does(
    visitor: TestClient, db: Session
) -> None:
    template = db.scalars(select(User).where(User.kind == UserKind.TEMPLATE.value)).one()

    def template_state() -> tuple[int, int]:
        db.expire_all()
        zones = select(HostedZone.id).where(HostedZone.owner_id == template.id)
        return (
            db.scalar(select(func.count()).select_from(zones.subquery())) or 0,
            db.scalar(select(func.count(RecordSet.id)).where(RecordSet.zone_id.in_(zones))) or 0,
        )

    before = template_state()
    assert before[0] == SEEDED_ZONES
    zone = _zones(visitor)[0]
    create_record(visitor, str(zone["id"]), "added", "A", ["192.0.2.50"])
    create_zone(visitor, "new.example")
    assert template_state() == before


# --- the sandbox follows the visitor ----------------------------------------------------


def test_signing_out_and_in_again_returns_to_the_same_sandbox(
    visitor: TestClient, settings: Settings
) -> None:
    create_zone(visitor, "kept.example")
    first = visitor.get(f"{API}/auth/me").json()["user"]

    assert visitor.post(f"{API}/auth/logout").status_code == 204
    assert visitor.get(f"{API}/hostedzones").status_code == 401
    second = _sign_in(visitor, settings)

    assert second == first
    assert "kept.example." in [zone["name"] for zone in _zones(visitor)]


def test_a_browser_without_the_cookie_gets_a_fresh_sandbox(
    visitor: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    create_zone(visitor, "kept.example")
    with TestClient(app) as fresh:
        _sign_in(fresh, settings)
        assert len(_zones(fresh)) == SEEDED_ZONES
    assert len(_sandboxes(db)) == 2


def test_a_forged_sandbox_cookie_starts_a_new_sandbox(
    app: FastAPI, settings: Settings, db: Session
) -> None:
    with TestClient(app) as client:
        response = client.post(
            f"{API}/auth/login",
            json={"email": settings.demo_email, "password": PASSWORD},
            headers={"Cookie": f"{settings.sandbox_cookie_name}=not-a-real-token"},
        )
    assert response.status_code == 200
    issued = response.cookies.get(settings.sandbox_cookie_name)
    assert issued
    assert issued != "not-a-real-token"
    assert len(_sandboxes(db)) == 1


def test_other_accounts_sign_in_to_themselves(app: FastAPI, db: Session) -> None:
    from app.services.auth import hash_password

    db.add(
        User(
            email="admin@example.com",
            password_hash=hash_password("another-password"),
            display_name="admin",
            account_id="999900001111",
        )
    )
    db.commit()
    with TestClient(app) as client:
        response = client.post(
            f"{API}/auth/login", json={"email": "admin@example.com", "password": "another-password"}
        )
        assert response.json()["user"]["email"] == "admin@example.com"
        assert _zones(client) == []
    assert _sandboxes(db) == []


# --- cleanup and limits -----------------------------------------------------------------


def test_an_idle_sandbox_is_deleted_with_everything_it_owns(
    visitor: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    stale = _sandboxes(db)[0]
    stale_key = stale.sandbox_key_hash
    stale_zone_ids = {zone["id"] for zone in _zones(visitor)}
    stale.last_seen_at = utcnow() - timedelta(days=settings.sandbox_idle_days, minutes=1)
    db.commit()

    with TestClient(app) as newcomer:
        _sign_in(newcomer, settings)
        assert len(_zones(newcomer)) == SEEDED_ZONES

    db.expire_all()
    remaining = _sandboxes(db)
    assert len(remaining) == 1
    assert remaining[0].sandbox_key_hash != stale_key
    assert (
        db.scalar(select(func.count(HostedZone.id)).where(HostedZone.id.in_(stale_zone_ids))) == 0
    )
    assert db.scalar(select(func.count()).select_from(AuthSession)) == 1
    # Nothing is left behind: every record still belongs to a zone that exists.
    orphans = select(func.count(RecordSet.id)).where(
        RecordSet.zone_id.not_in(select(HostedZone.id))
    )
    assert db.scalar(orphans) == 0
    assert visitor.get(f"{API}/auth/me").status_code == 401


def test_using_a_sandbox_keeps_it_alive(
    visitor: TestClient, app: FastAPI, settings: Settings, db: Session
) -> None:
    sandbox = _sandboxes(db)[0]
    almost_idle = utcnow() - timedelta(days=settings.sandbox_idle_days - 1)
    sandbox.last_seen_at = almost_idle
    session = db.scalars(select(AuthSession)).one()
    session.last_seen_at = almost_idle
    db.commit()

    assert visitor.get(f"{API}/hostedzones").status_code == 200
    db.expire_all()
    refreshed = db.get(User, sandbox.id)
    assert refreshed is not None
    assert refreshed.last_seen_at is not None
    assert utcnow() - refreshed.last_seen_at < timedelta(minutes=1)


def test_the_number_of_sandboxes_is_capped_by_dropping_the_stalest(
    settings: Settings, db: Session
) -> None:
    capped = settings.model_copy(update={"sandbox_max": 3})
    app = create_app(capped)
    clients = [TestClient(app) for _ in range(4)]
    try:
        first_ids = []
        for index, client in enumerate(clients[:3]):
            first_ids.append(_sign_in(client, capped)["id"])
            sandbox = db.get(User, first_ids[-1])
            assert sandbox is not None
            # Make the order of last use unambiguous: the first sandbox is the stalest.
            sandbox.last_seen_at = utcnow() - timedelta(hours=3 - index)
            db.commit()
        newest = _sign_in(clients[3], capped)["id"]
        assert newest not in first_ids
        db.expire_all()
        assert sorted(sandbox.id for sandbox in _sandboxes(db)) == sorted([*first_ids[1:], newest])
        assert clients[0].get(f"{API}/auth/me").status_code == 401
        assert clients[1].get(f"{API}/auth/me").status_code == 200
    finally:
        for client in clients:
            client.close()
        app.state.engine.dispose()


def test_one_address_can_only_start_so_many_sandboxes_an_hour(
    settings: Settings, db: Session
) -> None:
    limited = settings.model_copy(update={"sandbox_creations_per_hour": 2})
    app = create_app(limited)
    try:
        for _ in range(2):
            with TestClient(app) as client:
                _sign_in(client, limited)
        with TestClient(app) as third:
            response = third.post(
                f"{API}/auth/login", json={"email": limited.demo_email, "password": PASSWORD}
            )
            assert response.status_code == 429
            assert response.json()["code"] == "Throttling"
            assert int(response.headers["retry-after"]) > 3000
            assert "set-cookie" not in response.headers
        # Returning visitors and other addresses are not held up.
        with TestClient(app, client=("203.0.113.9", 40000)) as elsewhere:
            _sign_in(elsewhere, limited)
        assert len(_sandboxes(db)) == 3
    finally:
        app.state.engine.dispose()


def test_a_failed_sign_in_never_creates_a_sandbox(
    app: FastAPI, settings: Settings, db: Session
) -> None:
    with TestClient(app) as client:
        response = client.post(
            f"{API}/auth/login", json={"email": settings.demo_email, "password": "nope"}
        )
        assert response.status_code == 401
        assert settings.sandbox_cookie_name not in response.headers.get("set-cookie", "")
    assert _sandboxes(db) == []


# --- quotas -----------------------------------------------------------------------------


def test_hosted_zone_quota(settings: Settings, db: Session) -> None:
    # The ``db`` fixture's application has seeded the template in this database.
    app = create_app(settings.model_copy(update={"max_hosted_zones": SEEDED_ZONES + 1}))
    try:
        with TestClient(app) as client:
            _sign_in(client, settings)
            create_zone(client, "one-more.example")
            response = client.post(f"{API}/hostedzones", json={"name": "too-many.example"})
            assert response.status_code == 400
            assert response.json()["code"] == "TooManyHostedZones"
            assert len(_zones(client)) == SEEDED_ZONES + 1
    finally:
        app.state.engine.dispose()


def test_record_quota_applies_to_every_way_of_adding_records(settings: Settings) -> None:
    app = create_app(
        settings.model_copy(
            update={"demo_sandbox": False, "seed_demo_data": False, "max_records_per_zone": 4}
        )
    )
    try:
        with TestClient(app) as client:
            _sign_in(client, settings)
            zone_id = create_zone(client, "quota.example")["id"]  # NS + SOA: 2 of 4
            base = f"{API}/hostedzones/{zone_id}"
            create_record(client, zone_id, "a", "A", ["192.0.2.1"])
            create_record(client, zone_id, "b", "A", ["192.0.2.2"])

            single = client.post(
                f"{base}/records",
                json={"name": "c", "type": "A", "ttl": 60, "values": ["192.0.2.3"]},
            )
            assert single.status_code == 400
            assert single.json()["code"] == "LimitsExceeded"

            def change(action: str, name: str) -> dict[str, object]:
                return {
                    "action": action,
                    "record_set": {"name": name, "type": "A", "ttl": 60, "values": ["192.0.2.9"]},
                }

            over = client.post(f"{base}/records:batch", json={"changes": [change("CREATE", "c")]})
            assert over.status_code == 400
            assert over.json()["code"] == "LimitsExceeded"
            # A batch is judged by where it ends up, so swapping one record for another is fine.
            swap = client.post(
                f"{base}/records:batch",
                json={
                    "changes": [
                        {"action": "DELETE", "record_set": {"name": "a", "type": "A"}},
                        change("CREATE", "c"),
                    ]
                },
            )
            assert swap.status_code == 200, swap.text

            zone_file = "d 60 IN A 192.0.2.4\ne 60 IN A 192.0.2.5\n"
            preview = client.post(f"{base}/import", json={"content": zone_file}).json()
            assert [error["message"] for error in preview["errors"]] == [
                "This operation can't be completed because the hosted zone would exceed the "
                "limit of 4 records."
            ]
            imported = client.post(f"{base}/import", json={"content": zone_file, "dry_run": False})
            assert imported.status_code == 400
            assert imported.json()["code"] == "InvalidZoneFile"

            assert client.get(base).json()["record_count"] == 4
    finally:
        app.state.engine.dispose()
