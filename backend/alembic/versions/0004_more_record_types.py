"""Record types DS, HTTPS, NAPTR, SPF, SSHFP, SVCB and TLSA.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BEFORE = ("A", "AAAA", "CAA", "CNAME", "MX", "NS", "PTR", "SOA", "SRV", "TXT")
_ADDED = ("DS", "HTTPS", "NAPTR", "SPF", "SSHFP", "SVCB", "TLSA")


def _type_in(types: Sequence[str]) -> str:
    return "type IN ({})".format(", ".join(f"'{name}'" for name in types))


def _replace_type_check(types: Sequence[str]) -> None:
    with op.batch_alter_table("record_sets") as batch:
        batch.drop_constraint(op.f("ck_record_sets_type_valid"), type_="check")
        batch.create_check_constraint(op.f("ck_record_sets_type_valid"), _type_in(types))


def upgrade() -> None:
    _replace_type_check(sorted(_BEFORE + _ADDED))


def downgrade() -> None:
    # Records of the added types cannot be kept under the narrower check.
    added = ", ".join(f"'{name}'" for name in _ADDED)
    records = f"SELECT id FROM record_sets WHERE type IN ({added})"
    op.execute(f"DELETE FROM record_values WHERE record_set_id IN ({records})")
    op.execute(f"DELETE FROM record_sets WHERE type IN ({added})")
    _replace_type_check(_BEFORE)
