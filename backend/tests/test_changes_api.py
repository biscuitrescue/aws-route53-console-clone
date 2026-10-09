"""The simulated change status: PENDING for a while after a record change, then INSYNC."""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.models import Change, User
from app.models.base import utcnow
from app.services.auth import hash_password
from tests.conftest import API, create_record, create_zone


def _batch(client: TestClient, zone_id: str, *names: str, comment: str = "") -> Any:
    changes = [
        {
            "action": "CREATE",
            "record_set": {"name": name, "type": "A", "ttl": 60, "values": ["192.0.2.1"]},
        }
        for name in names
    ]
    return client.post(
        f"{API}/hostedzones/{zone_id}/records:batch", json={"comment": comment, "changes": changes}
    )


def _age(db: Session, change_id: str, seconds: float) -> None:
    change = db.get(Change, change_id)
    assert change is not None
    change.submitted_at = utcnow() - timedelta(seconds=seconds)
    db.commit()


def test_a_batch_answers_with_a_pending_change(
    client: TestClient, zone: dict[str, Any], settings: Settings
) -> None:
    body = _batch(client, zone["id"], "a", "b", comment="add two").json()
    assert body["status"] == "PENDING"
    assert body["comment"] == "add two"
    assert body["id"].startswith("C")
    assert len(body["id"]) == 14

    fetched = client.get(f"{API}/changes/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == {
        "id": body["id"],
        "status": "PENDING",
        "comment": "add two",
        "submitted_at": body["submitted_at"],
    }


def test_a_change_becomes_insync_after_the_propagation_delay(
    client: TestClient, zone: dict[str, Any], settings: Settings, db: Session
) -> None:
    change_id = _batch(client, zone["id"], "a").json()["id"]
    url = f"{API}/changes/{change_id}"

    _age(db, change_id, settings.change_propagation_seconds - 2)
    assert client.get(url).json()["status"] == "PENDING"

    _age(db, change_id, settings.change_propagation_seconds)
    assert client.get(url).json()["status"] == "INSYNC"
    # It stays that way, and the record it made was there all along.
    assert client.get(url).json()["status"] == "INSYNC"
    assert client.get(f"{API}/hostedzones/{zone['id']}").json()["record_count"] == 3


def test_the_delay_is_configurable(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"change_propagation_seconds": 0}))
    with TestClient(app) as client:
        client.post(
            f"{API}/auth/login",
            json={"email": settings.demo_email, "password": settings.demo_password},
        )
        zone_id = create_zone(client)["id"]
        assert _batch(client, zone_id, "a").json()["status"] == "INSYNC"
    app.state.engine.dispose()


def test_each_change_has_its_own_status(
    client: TestClient, zone: dict[str, Any], settings: Settings, db: Session
) -> None:
    first = _batch(client, zone["id"], "a").json()["id"]
    second = _batch(client, zone["id"], "b").json()["id"]
    assert first != second

    _age(db, first, settings.change_propagation_seconds + 1)
    assert client.get(f"{API}/changes/{first}").json()["status"] == "INSYNC"
    assert client.get(f"{API}/changes/{second}").json()["status"] == "PENDING"


def test_single_record_routes_name_their_change_in_a_header(
    client: TestClient, zone: dict[str, Any]
) -> None:
    base = f"{API}/hostedzones/{zone['id']}/records"
    created = client.post(
        base, json={"name": "www", "type": "A", "ttl": 60, "values": ["192.0.2.1"]}
    )
    updated = client.patch(f"{base}/{created.json()['id']}", json={"ttl": 120})
    deleted = client.delete(f"{base}/{created.json()['id']}")

    ids = [response.headers["x-change-id"] for response in (created, updated, deleted)]
    assert len(set(ids)) == 3
    for change_id in ids:
        assert client.get(f"{API}/changes/{change_id}").json()["status"] == "PENDING"


def test_an_import_names_its_change_and_a_preview_makes_none(
    client: TestClient, zone: dict[str, Any], db: Session
) -> None:
    url = f"{API}/hostedzones/{zone['id']}/import"
    content = "www 60 IN A 192.0.2.1\n"

    preview = client.post(url, json={"content": content}).json()
    assert preview["change_id"] is None
    assert db.scalar(select(func.count(Change.id))) == 0

    imported = client.post(url, json={"content": content, "dry_run": False}).json()
    assert (
        client.get(f"{API}/changes/{imported['change_id']}").json()["comment"] == "Zone file import"
    )


def test_a_rejected_change_leaves_no_change_behind(
    client: TestClient, zone: dict[str, Any], db: Session
) -> None:
    base = f"{API}/hostedzones/{zone['id']}/records"
    create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    before = db.scalar(select(func.count(Change.id)))

    duplicate = client.post(
        base, json={"name": "www", "type": "A", "ttl": 60, "values": ["192.0.2.2"]}
    )
    invalid = client.post(base, json={"name": "bad", "type": "A", "ttl": 60, "values": ["nope"]})
    batch = client.post(
        f"{base}:batch",
        json={"changes": [{"action": "DELETE", "record_set": {"name": "missing", "type": "A"}}]},
    )
    assert (duplicate.status_code, invalid.status_code, batch.status_code) == (409, 400, 400)
    assert "x-change-id" not in duplicate.headers
    assert db.scalar(select(func.count(Change.id))) == before


def test_an_unknown_change_is_not_found(client: TestClient) -> None:
    response = client.get(f"{API}/changes/C0000000000000")
    assert response.status_code == 404
    assert response.json() == {
        "code": "NoSuchChange",
        "message": "No change found with ID: C0000000000000",
        "details": [],
    }


def test_changes_need_a_session_and_belong_to_the_zones_owner(
    client: TestClient, anonymous: TestClient, zone: dict[str, Any], db: Session
) -> None:
    change_id = _batch(client, zone["id"], "a").json()["id"]
    assert anonymous.get(f"{API}/changes/{change_id}").status_code == 401

    db.add(
        User(
            email="other@example.com",
            password_hash=hash_password("their-password"),
            display_name="other",
            account_id="222233334444",
        )
    )
    db.commit()
    login = anonymous.post(
        f"{API}/auth/login", json={"email": "other@example.com", "password": "their-password"}
    )
    assert login.status_code == 200
    assert anonymous.get(f"{API}/changes/{change_id}").json()["code"] == "NoSuchChange"


def test_changes_go_with_their_zone_and_old_ones_are_dropped(
    client: TestClient, zone: dict[str, Any], db: Session
) -> None:
    old = _batch(client, zone["id"], "a").json()["id"]
    _age(db, old, 2 * 86_400)
    recent = _batch(client, zone["id"], "b").json()["id"]
    # Recording the newer change dropped the one from two days ago.
    assert client.get(f"{API}/changes/{old}").status_code == 404
    assert client.get(f"{API}/changes/{recent}").status_code == 200

    removal = [
        {"action": "DELETE", "record_set": {"name": name, "type": "A"}} for name in ("a", "b")
    ]
    client.post(f"{API}/hostedzones/{zone['id']}/records:batch", json={"changes": removal})
    assert client.delete(f"{API}/hostedzones/{zone['id']}").status_code == 204
    assert client.get(f"{API}/changes/{recent}").status_code == 404
    assert db.scalar(select(func.count(Change.id))) == 0
