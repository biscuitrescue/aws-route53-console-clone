"""The migrations must produce exactly the schema the models describe."""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import create_db_engine
from app.models import Base
from tests.conftest import alembic_config


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
