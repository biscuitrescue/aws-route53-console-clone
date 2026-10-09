"""The migrations must produce exactly the schema the models describe."""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import create_db_engine, create_session_factory
from app.main import create_app
from app.models import Base, User
from app.seed import seed, seed_demo_zones
from tests.conftest import API, PASSWORD, alembic_config, make_settings


def _first_release_user(db: Session, settings: Settings) -> User:
    """Insert the demo user with the columns the first schema had."""
    db.execute(
        text(
            "INSERT INTO users (email, password_hash, display_name, account_id, created_at) "
            "VALUES (:email, 'x', 'demo-admin', '111122223333', '2026-10-09 00:00:00')"
        ),
        {"email": settings.demo_email},
    )
    db.commit()
    return User(id=1, email=settings.demo_email)


def test_migrations_match_the_models(settings: Settings) -> None:
    engine = create_db_engine(settings.database_url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []
    engine.dispose()


def test_migrations_can_be_reversed(tmp_path: Path) -> None:
    database = tmp_path / "reversible.db"
    config = alembic_config(database)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_db_engine(f"sqlite:///{database}")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def _dump(database: Path, tables: list[str]) -> dict[str, list[tuple[object, ...]]]:
    engine = create_db_engine(f"sqlite:///{database}")
    with engine.connect() as connection:
        rows = {
            table: [tuple(row) for row in connection.execute(text(f"SELECT * FROM {table}"))]
            for table in tables
        }
    engine.dispose()
    return rows


def test_migrating_a_database_in_use_keeps_every_row(tmp_path: Path) -> None:
    """Later migrations rebuild tables; that must not cascade into the rows that refer to them."""
    database = tmp_path / "in-use.db"
    config = alembic_config(database)
    command.upgrade(config, "0001")

    settings = make_settings(database, seed_demo_data=True)
    engine = create_db_engine(settings.database_url)
    with create_session_factory(engine)() as db:
        # What the first release's seed did: the sample zones belong to the demo user.
        seed_demo_zones(db, _first_release_user(db, settings))
    engine.dispose()

    children = [
        "hosted_zones",
        "hosted_zone_vpcs",
        "hosted_zone_tags",
        "record_sets",
        "record_values",
    ]
    before = _dump(database, children)
    assert len(before["hosted_zones"]) == 12
    assert len(before["record_values"]) > 50

    command.upgrade(config, "head")
    assert _dump(database, children) == before

    command.downgrade(config, "0001")
    assert _dump(database, children) == before


def test_downgrading_removes_sandboxes_and_everything_they_own(tmp_path: Path) -> None:
    database = tmp_path / "sandboxes.db"
    config = alembic_config(database)
    command.upgrade(config, "head")
    settings = make_settings(database, seed_demo_data=True, demo_sandbox=True)
    app = create_app(settings)
    with app.state.session_factory() as db:
        seed(db, settings)
    with TestClient(app) as client:
        login = client.post(
            f"{API}/auth/login", json={"email": settings.demo_email, "password": PASSWORD}
        )
        assert login.status_code == 200
    app.state.engine.dispose()

    command.downgrade(config, "0001")
    rows = _dump(database, ["users", "sessions", "hosted_zones", "record_sets", "record_values"])
    assert len(rows["users"]) == 1
    assert rows["sessions"] == rows["hosted_zones"] == rows["record_sets"] == []
    assert rows["record_values"] == []


def test_connections_enforce_foreign_keys_and_use_wal(db: Session) -> None:
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert db.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_foreign_keys_are_enforced(db: Session) -> None:
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO record_values (record_set_id, position, value) "
                "VALUES ('missing', 0, 'x')"
            )
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE record_sets SET type = 'BOGUS'",
        "UPDATE record_sets SET ttl = -1",
        "UPDATE record_sets SET ttl = NULL",
        "UPDATE record_sets SET routing_policy = 'random'",
        "UPDATE record_sets SET weight = 256",
        "UPDATE hosted_zones SET type = 'hybrid'",
    ],
)
def test_check_constraints_guard_the_data(
    db: Session, zone: dict[str, object], statement: str
) -> None:
    with pytest.raises(IntegrityError):
        db.execute(text(statement))
