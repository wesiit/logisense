"""Create licenses table.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the license schema if it doesn't exist
    op.execute("CREATE SCHEMA IF NOT EXISTS license")

    # Create the licenses table
    op.create_table(
        "licenses",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("licensed_modules", postgresql.JSONB, nullable=False, default=[]),
        sa.Column("facility_count", sa.Integer, nullable=False, default=1),
        sa.Column("tier", sa.String(50), nullable=False, default="standard"),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("token_hash", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        schema="license",
    )


def downgrade() -> None:
    op.drop_table("licenses", schema="license")
    op.execute("DROP SCHEMA IF EXISTS license")
