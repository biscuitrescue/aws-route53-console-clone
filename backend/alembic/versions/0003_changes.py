"""Changes: one row per accepted change to a zone's records, for its simulated status.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "changes",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("zone_id", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.String(length=256), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["hosted_zones.id"],
            name=op.f("fk_changes_zone_id_hosted_zones"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_changes")),
    )
    op.create_index("ix_changes_zone_submitted_at", "changes", ["zone_id", "submitted_at"])


def downgrade() -> None:
    op.drop_index("ix_changes_zone_submitted_at", table_name="changes")
    op.drop_table("changes")
