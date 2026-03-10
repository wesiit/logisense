"""Create uoih.alerts table.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create uoih schema
    op.execute("CREATE SCHEMA IF NOT EXISTS uoih")

    # Create alerts table
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("facility_id", sa.String(50), nullable=False, index=True),
        sa.Column("module_id", sa.String(50), nullable=False),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column(
            "severity", sa.String(20), nullable=False
        ),  # CRITICAL/HIGH/MEDIUM/LOW
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="ACTIVE"
        ),  # ACTIVE/ACKNOWLEDGED/RESOLVED
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("acknowledged_by", sa.String(100), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        schema="uoih",
    )

    # Create indexes
    op.create_index(
        "ix_uoih_alerts_facility_status",
        "alerts",
        ["facility_id", "status"],
        schema="uoih",
    )
    op.create_index(
        "ix_uoih_alerts_severity_created",
        "alerts",
        ["severity", "created_at"],
        schema="uoih",
    )
    op.create_index(
        "ix_uoih_alerts_module_type",
        "alerts",
        ["module_id", "alert_type"],
        schema="uoih",
    )


def downgrade() -> None:
    op.drop_index("ix_uoih_alerts_module_type", table_name="alerts", schema="uoih")
    op.drop_index("ix_uoih_alerts_severity_created", table_name="alerts", schema="uoih")
    op.drop_index("ix_uoih_alerts_facility_status", table_name="alerts", schema="uoih")
    op.drop_table("alerts", schema="uoih")
    op.execute("DROP SCHEMA IF EXISTS uoih")
