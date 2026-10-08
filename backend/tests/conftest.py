"""Fixtures: every test gets its own SQLite file, created by the real migrations."""

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import create_db_engine, create_session_factory
from app.main import create_app
from app.seed import ensure_demo_user

BACKEND_DIR = Path(__file__).resolve().parent.parent
API = "/api/v1"
PASSWORD = "correct-horse-battery"


def make_settings(database: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "test",
        "database_url": f"sqlite:///{database}",
        "demo_password": PASSWORD,
        "seed_demo_data": False,
    }
    return Settings(**(values | overrides))


def alembic_config(database: Path) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    return config


@pytest.fixture(scope="session")
def template_database(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A migrated database holding only the demo user; copied for each test."""
    database = tmp_path_factory.mktemp("template") / "template.db"
    command.upgrade(alembic_config(database), "head")
    engine = create_db_engine(f"sqlite:///{database}")
    with create_session_factory(engine)() as db:
        ensure_demo_user(db, make_settings(database))
    engine.dispose()
    return database


@pytest.fixture
def settings(tmp_path: Path, template_database: Path) -> Settings:
    database = tmp_path / "route53.db"
    shutil.copy(template_database, database)
    return make_settings(database)


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def db(app: FastAPI) -> Iterator[Session]:
    with app.state.session_factory() as session:
        yield session


@pytest.fixture
def anonymous(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(app: FastAPI, settings: Settings) -> Iterator[TestClient]:
    """A client that is signed in as the demo user."""
    with TestClient(app) as test_client:
        response = test_client.post(
            f"{API}/auth/login", json={"email": settings.demo_email, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        yield test_client


def create_zone(client: TestClient, name: str = "example.com", **fields: Any) -> dict[str, Any]:
    response = client.post(f"{API}/hostedzones", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    zone: dict[str, Any] = response.json()
    return zone


def create_record(
    client: TestClient, zone_id: str, name: str, record_type: str, values: list[str], **fields: Any
) -> dict[str, Any]:
    payload = {"name": name, "type": record_type, "ttl": 300, "values": values, **fields}
    response = client.post(f"{API}/hostedzones/{zone_id}/records", json=payload)
    assert response.status_code == 201, response.text
    record: dict[str, Any] = response.json()
    return record


@pytest.fixture
def zone(client: TestClient) -> dict[str, Any]:
    return create_zone(client)
