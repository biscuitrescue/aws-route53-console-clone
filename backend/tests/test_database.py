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
from app.models import Base
from app.seed import ensure_demo_user, seed, seed_demo_zones
from tests.conftest import API, PASSWORD, alembic_config, make_settings


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


# Position of `type` in a row of `record_sets`.
_RECORD_TYPE_COLUMN = 4


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
    """Migrations rebuild tables; that must not cascade into the rows that refer to them."""
    database = tmp_path / "in-use.db"
    config = alembic_config(database)
    command.upgrade(config, "head")

    # A database as the first release left it: the sample zones belong to the demo user.
    settings = make_settings(database, seed_demo_data=True)
    engine = create_db_engine(settings.database_url)
    with create_session_factory(engine)() as db:
        seed_demo_zones(db, ensure_demo_user(db, settings))
    engine.dispose()

    tables = [
        "hosted_zones",
        "hosted_zone_vpcs",
        "hosted_zone_tags",
        "record_sets",
        "record_values",
    ]
    seeded = _dump(database, tables)
    assert len(seeded["hosted_zones"]) == 12
    assert len(seeded["record_values"]) > 50

    # Going back to the first schema drops the record types it did not have, and only those.
    first_types = ("A", "AAAA", "CAA", "CNAME", "MX", "NS", "PTR", "SOA", "SRV", "TXT")
    kept_sets = [row for row in seeded["record_sets"] if row[_RECORD_TYPE_COLUMN] in first_types]
    kept_ids = {row[0] for row in kept_sets}
    assert 0 < len(seeded["record_sets"]) - len(kept_sets) < 10
    expected = seeded | {
        "record_sets": kept_sets,
        "record_values": [row for row in seeded["record_values"] if row[0] in kept_ids],
    }

    command.downgrade(config, "0001")
    assert _dump(database, tables) == expected
    assert len(_dump(database, ["users"])["users"]) == 1

    # Upgrading again rebuilds `users` and `record_sets` with rows that refer to them.
    command.upgrade(config, "head")
    assert _dump(database, tables) == expected
    assert len(_dump(database, ["users"])["users"]) == 1


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
