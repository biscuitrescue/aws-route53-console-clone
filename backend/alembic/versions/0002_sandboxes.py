"""Per-visitor sandboxes: what a user row is, its sandbox key and when it was last used.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # AUTOINCREMENT, so the ID of a deleted sandbox is never given to a new one.
    with op.batch_alter_table("users", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.add_column(
            sa.Column("kind", sa.String(length=16), nullable=False, server_default="account")
        )
        batch.add_column(sa.Column("sandbox_key_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint(op.f("uq_users_sandbox_key_hash"), ["sandbox_key_hash"])
        batch.create_check_constraint(
            op.f("ck_users_kind_valid"), "kind IN ('account', 'template', 'sandbox')"
        )
        batch.create_index("ix_users_kind_last_seen_at", ["kind", "last_seen_at"])


def downgrade() -> None:
    # Sandboxes and the template are rows the older schema cannot tell from accounts, so
    # they go, with what they own. Foreign keys are not enforced during a migration (see
    # env.py), so nothing cascades and each table is cleared explicitly.
    owners = "SELECT id FROM users WHERE kind != 'account'"
    zones = f"SELECT id FROM hosted_zones WHERE owner_id IN ({owners})"
    records = f"SELECT id FROM record_sets WHERE zone_id IN ({zones})"
    op.execute(f"DELETE FROM record_values WHERE record_set_id IN ({records})")
    op.execute(f"DELETE FROM record_sets WHERE zone_id IN ({zones})")
    op.execute(f"DELETE FROM hosted_zone_tags WHERE zone_id IN ({zones})")
    op.execute(f"DELETE FROM hosted_zone_vpcs WHERE zone_id IN ({zones})")
    op.execute(f"DELETE FROM hosted_zones WHERE owner_id IN ({owners})")
    op.execute(f"DELETE FROM sessions WHERE user_id IN ({owners})")
    op.execute("DELETE FROM users WHERE kind != 'account'")
    with op.batch_alter_table("users", table_kwargs={"sqlite_autoincrement": False}) as batch:
        batch.drop_index("ix_users_kind_last_seen_at")
        batch.drop_constraint(op.f("ck_users_kind_valid"), type_="check")
        batch.drop_constraint(op.f("uq_users_sandbox_key_hash"), type_="unique")
        batch.drop_column("last_seen_at")
        batch.drop_column("sandbox_key_hash")
        batch.drop_column("kind")
