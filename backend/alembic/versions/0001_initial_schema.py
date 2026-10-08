"""Initial schema: users, sessions, hosted zones (VPCs, tags), record sets and values.

Revision ID: 0001
Revises:
Create Date: 2026-10-09

Timestamps are naive UTC; the application converts them (see ``app.models.base``).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "hosted_zones",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_key", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=False),
        sa.Column("caller_reference", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "type IN ('public', 'private')", name=op.f("ck_hosted_zones_type_valid")
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_hosted_zones_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hosted_zones")),
        sa.UniqueConstraint("caller_reference", name=op.f("uq_hosted_zones_caller_reference")),
    )
    with op.batch_alter_table("hosted_zones", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_hosted_zones_name"), ["name"], unique=False)
        batch_op.create_index(batch_op.f("ix_hosted_zones_owner_id"), ["owner_id"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token_hash", name=op.f("pk_sessions")),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_index("ix_sessions_expires_at", ["expires_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_sessions_user_id"), ["user_id"], unique=False)

    op.create_table(
        "hosted_zone_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("zone_id", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["hosted_zones.id"],
            name=op.f("fk_hosted_zone_tags_zone_id_hosted_zones"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hosted_zone_tags")),
        sa.UniqueConstraint("zone_id", "key", name=op.f("uq_hosted_zone_tags_zone_id_key")),
    )
    op.create_table(
        "hosted_zone_vpcs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("zone_id", sa.String(length=32), nullable=False),
        sa.Column("vpc_id", sa.String(length=32), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["hosted_zones.id"],
            name=op.f("fk_hosted_zone_vpcs_zone_id_hosted_zones"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hosted_zone_vpcs")),
        sa.UniqueConstraint("zone_id", "vpc_id", name=op.f("uq_hosted_zone_vpcs_zone_id_vpc_id")),
    )
    op.create_table(
        "record_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("zone_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_key", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=8), nullable=False),
        sa.Column("ttl", sa.Integer(), nullable=True),
        sa.Column("routing_policy", sa.String(length=16), nullable=False),
        sa.Column("set_identifier", sa.String(length=128), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("region", sa.String(length=32), nullable=True),
        sa.Column("failover", sa.String(length=16), nullable=True),
        sa.Column("geo_continent_code", sa.String(length=2), nullable=True),
        sa.Column("geo_country_code", sa.String(length=2), nullable=True),
        sa.Column("geo_subdivision_code", sa.String(length=3), nullable=True),
        sa.Column("health_check_id", sa.String(length=64), nullable=True),
        sa.Column("is_alias", sa.Boolean(), nullable=False),
        sa.Column("alias_target_dns_name", sa.String(length=255), nullable=True),
        sa.Column("alias_target_hosted_zone_id", sa.String(length=32), nullable=True),
        sa.Column("evaluate_target_health", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "failover IS NULL OR failover IN ('PRIMARY', 'SECONDARY')",
            name=op.f("ck_record_sets_failover_valid"),
        ),
        sa.CheckConstraint(
            "routing_policy IN ('simple', 'weighted', 'latency', 'failover', 'geolocation', 'multivalue')",
            name=op.f("ck_record_sets_routing_policy_valid"),
        ),
        sa.CheckConstraint(
            "type IN ('A', 'AAAA', 'CAA', 'CNAME', 'MX', 'NS', 'PTR', 'SOA', 'SRV', 'TXT')",
            name=op.f("ck_record_sets_type_valid"),
        ),
        sa.CheckConstraint(
            "(is_alias = 1 AND ttl IS NULL AND alias_target_dns_name IS NOT NULL) OR (is_alias = 0 AND ttl IS NOT NULL AND alias_target_dns_name IS NULL)",
            name=op.f("ck_record_sets_alias_shape"),
        ),
        sa.CheckConstraint(
            "ttl IS NULL OR (ttl >= 0 AND ttl <= 2147483647)", name=op.f("ck_record_sets_ttl_range")
        ),
        sa.CheckConstraint(
            "weight IS NULL OR (weight >= 0 AND weight <= 255)",
            name=op.f("ck_record_sets_weight_range"),
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["hosted_zones.id"],
            name=op.f("fk_record_sets_zone_id_hosted_zones"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_sets")),
        sa.UniqueConstraint(
            "zone_id", "name", "type", "set_identifier", name="uq_record_sets_identity"
        ),
    )
    with op.batch_alter_table("record_sets", schema=None) as batch_op:
        batch_op.create_index(
            "ix_record_sets_zone_sort", ["zone_id", "sort_key", "type"], unique=False
        )
        batch_op.create_index("ix_record_sets_zone_type", ["zone_id", "type"], unique=False)

    op.create_table(
        "record_values",
        sa.Column("record_set_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_set_id"],
            ["record_sets.id"],
            name=op.f("fk_record_values_record_set_id_record_sets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("record_set_id", "position", name=op.f("pk_record_values")),
    )
    with op.batch_alter_table("record_values", schema=None) as batch_op:
        batch_op.create_index("ix_record_values_value", ["value"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("record_values", schema=None) as batch_op:
        batch_op.drop_index("ix_record_values_value")

    op.drop_table("record_values")
    with op.batch_alter_table("record_sets", schema=None) as batch_op:
        batch_op.drop_index("ix_record_sets_zone_type")
        batch_op.drop_index("ix_record_sets_zone_sort")

    op.drop_table("record_sets")
    op.drop_table("hosted_zone_vpcs")
    op.drop_table("hosted_zone_tags")
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sessions_user_id"))
        batch_op.drop_index("ix_sessions_expires_at")

    op.drop_table("sessions")
    with op.batch_alter_table("hosted_zones", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_hosted_zones_owner_id"))
        batch_op.drop_index(batch_op.f("ix_hosted_zones_name"))

    op.drop_table("hosted_zones")
    op.drop_table("users")
