"""Alembic environment: migrations run against the database the application uses."""

from logging.config import fileConfig

from alembic import context

from app.config import get_settings
from app.db import create_db_engine
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(_database_url())
    with engine.connect() as connection:
        # A batch migration rebuilds a table and drops the old one. With foreign keys
        # enforced, SQLite treats that drop as deleting every row and cascades it: altering
        # `users` would delete every hosted zone. So enforcement is off while migrating,
        # as SQLite's procedure for altering tables prescribes, and the result is checked.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 0:
            raise RuntimeError("Could not turn foreign key enforcement off for the migration")
        # End the transaction these statements opened, so Alembic manages its own.
        connection.commit()

        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()

        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        connection.rollback()
        if violations:
            raise RuntimeError(f"The migration left dangling references: {violations[:5]}")
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
