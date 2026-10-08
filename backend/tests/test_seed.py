from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.enums import RecordType
from app.main import create_app
from app.models import HostedZone, RecordSet, User
from app.seed import seed
from tests.conftest import API, PASSWORD, create_record, create_zone


def _counts(db: Session) -> tuple[int, int, int]:
    return (
        db.scalar(select(func.count(User.id))) or 0,
        db.scalar(select(func.count(HostedZone.id))) or 0,
        db.scalar(select(func.count(RecordSet.id))) or 0,
    )


def test_seed_creates_the_demo_data_once(db: Session, settings: Settings) -> None:
    seeding = settings.model_copy(update={"seed_demo_data": True})
    seed(db, seeding)
    first = _counts(db)
    assert first[0] == 1
    assert first[1] == 12
    assert first[2] > 50

    seed(db, seeding)
    assert _counts(db) == first


def test_seeded_data_covers_every_record_type_and_zone_type(
    db: Session, settings: Settings
) -> None:
    seed(db, settings.model_copy(update={"seed_demo_data": True}))
    assert set(db.scalars(select(RecordSet.type).distinct())) == {t.value for t in RecordType}
    assert set(db.scalars(select(HostedZone.type).distinct())) == {"public", "private"}
    assert db.scalar(select(func.count(RecordSet.id)).where(RecordSet.is_alias)) == 1


def test_seed_leaves_existing_zones_alone(
    client: TestClient, db: Session, settings: Settings
) -> None:
    create_zone(client, "mine.com")
    seed(db, settings.model_copy(update={"seed_demo_data": True}))
    assert _counts(db)[1] == 1


def test_seed_can_skip_the_demo_zones(db: Session, settings: Settings) -> None:
    seed(db, settings)
    assert _counts(db) == (1, 0, 0)


def test_data_survives_an_application_restart(
    client: TestClient, app: FastAPI, settings: Settings
) -> None:
    zone = create_zone(client, "durable.com", description="still here")
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    app.state.engine.dispose()

    restarted = create_app(settings)
    with TestClient(restarted) as fresh:
        fresh.post(f"{API}/auth/login", json={"email": settings.demo_email, "password": PASSWORD})
        assert fresh.get(f"{API}/hostedzones/{zone['id']}").json()["description"] == "still here"
        fetched = fresh.get(f"{API}/hostedzones/{zone['id']}/records/{record['id']}")
        assert fetched.json() == record
    restarted.state.engine.dispose()

    database = Path(settings.database_url.removeprefix("sqlite:///"))
    assert database.stat().st_size > 0
