"""Create iWMS schema and tables.

Revision ID: 0001
Revises:
Create Date: 2024-01-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Schema name
SCHEMA = "iwms"


def upgrade() -> None:  # noqa: PLR0915
    # Create schema
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # =========================================================================
    # locations - Warehouse location master
    # =========================================================================
    op.create_table(
        "locations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("facility_id", sa.String(50), nullable=False),
        sa.Column("zone_id", sa.String(50), nullable=True),
        sa.Column("aisle", sa.String(20), nullable=True),
        sa.Column("bay", sa.String(20), nullable=True),
        sa.Column("level", sa.String(20), nullable=True),
        sa.Column("bin", sa.String(20), nullable=True),
        sa.Column("location_code", sa.String(100), nullable=False, unique=True),
        sa.Column("location_type", sa.String(50), nullable=True),
        sa.Column("max_weight_kg", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_locations_facility_id", "locations", ["facility_id"], schema=SCHEMA
    )
    op.create_index("ix_locations_zone_id", "locations", ["zone_id"], schema=SCHEMA)
    op.create_index(
        "ix_locations_location_type", "locations", ["location_type"], schema=SCHEMA
    )
    op.create_index("ix_locations_is_active", "locations", ["is_active"], schema=SCHEMA)

    # =========================================================================
    # skus - Product/SKU master
    # =========================================================================
    op.create_table(
        "skus",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("sku_code", sa.String(100), nullable=False, unique=True),
        sa.Column("sku_name", sa.String(500), nullable=False),
        sa.Column("category_l1", sa.String(100), nullable=True),
        sa.Column("category_l2", sa.String(100), nullable=True),
        sa.Column("unit_of_measure", sa.String(20), nullable=True),
        sa.Column("weight_kg", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "is_perishable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("temperature_zone", sa.String(50), nullable=True),
        sa.Column("reorder_point", sa.Integer(), nullable=True),
        sa.Column("min_order_qty", sa.Integer(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_skus_sku_code", "skus", ["sku_code"], schema=SCHEMA)
    op.create_index("ix_skus_category_l1", "skus", ["category_l1"], schema=SCHEMA)
    op.create_index("ix_skus_is_perishable", "skus", ["is_perishable"], schema=SCHEMA)
    op.create_index(
        "ix_skus_temperature_zone", "skus", ["temperature_zone"], schema=SCHEMA
    )
    op.create_index("ix_skus_is_active", "skus", ["is_active"], schema=SCHEMA)

    # =========================================================================
    # inventory_positions - Current inventory state
    # =========================================================================
    op.create_table(
        "inventory_positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("facility_id", sa.String(50), nullable=False),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.locations.id"),
            nullable=False,
        ),
        sa.Column(
            "sku_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.skus.id"),
            nullable=False,
        ),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column(
            "quantity", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "quantity_reserved",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("received_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_counted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_movement_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "facility_id",
            "location_id",
            "sku_id",
            "lot_number",
            name="uq_inventory_position",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_positions_facility_id",
        "inventory_positions",
        ["facility_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_positions_location_id",
        "inventory_positions",
        ["location_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_positions_sku_id",
        "inventory_positions",
        ["sku_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_positions_lot_number",
        "inventory_positions",
        ["lot_number"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_positions_expiry_date",
        "inventory_positions",
        ["expiry_date"],
        schema=SCHEMA,
    )

    # =========================================================================
    # inventory_movements - Inventory transaction history
    # =========================================================================
    op.create_table(
        "inventory_movements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("facility_id", sa.String(50), nullable=False),
        sa.Column(
            "movement_type",
            sa.String(20),
            nullable=False,
            comment="RECEIVE, PICK, PUTAWAY, TRANSFER, ADJUST, CYCLE_COUNT",
        ),
        sa.Column(
            "from_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.locations.id"),
            nullable=True,
        ),
        sa.Column(
            "to_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.locations.id"),
            nullable=True,
        ),
        sa.Column(
            "sku_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.skus.id"),
            nullable=False,
        ),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("performed_by", sa.String(100), nullable=True),
        sa.Column(
            "performed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_facility_id",
        "inventory_movements",
        ["facility_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_movement_type",
        "inventory_movements",
        ["movement_type"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_sku_id",
        "inventory_movements",
        ["sku_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_from_location_id",
        "inventory_movements",
        ["from_location_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_to_location_id",
        "inventory_movements",
        ["to_location_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_performed_at",
        "inventory_movements",
        ["performed_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_movements_reference_id",
        "inventory_movements",
        ["reference_id"],
        schema=SCHEMA,
    )

    # =========================================================================
    # orders - Outbound/transfer/return orders
    # =========================================================================
    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("facility_id", sa.String(50), nullable=False),
        sa.Column("order_number", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "order_type",
            sa.String(20),
            nullable=False,
            comment="OUTBOUND, TRANSFER, RETURN",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
            comment="PENDING, WAVED, PICKING, PACKED, DISPATCHED, CANCELLED",
        ),
        sa.Column(
            "priority", sa.Integer(), nullable=False, server_default=sa.text("5")
        ),
        sa.Column("customer_id", sa.String(100), nullable=True),
        sa.Column("carrier_code", sa.String(50), nullable=True),
        sa.Column("required_ship_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_orders_facility_id", "orders", ["facility_id"], schema=SCHEMA)
    op.create_index("ix_orders_order_number", "orders", ["order_number"], schema=SCHEMA)
    op.create_index("ix_orders_order_type", "orders", ["order_type"], schema=SCHEMA)
    op.create_index("ix_orders_status", "orders", ["status"], schema=SCHEMA)
    op.create_index("ix_orders_priority", "orders", ["priority"], schema=SCHEMA)
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"], schema=SCHEMA)
    op.create_index(
        "ix_orders_required_ship_date", "orders", ["required_ship_date"], schema=SCHEMA
    )

    # =========================================================================
    # order_lines - Order line items
    # =========================================================================
    op.create_table(
        "order_lines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sku_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.skus.id"),
            nullable=False,
        ),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column(
            "quantity_picked", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
            comment="PENDING, IN_PROGRESS, COMPLETE, SHORT",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_order_lines_order_id", "order_lines", ["order_id"], schema=SCHEMA
    )
    op.create_index("ix_order_lines_sku_id", "order_lines", ["sku_id"], schema=SCHEMA)
    op.create_index("ix_order_lines_status", "order_lines", ["status"], schema=SCHEMA)

    # =========================================================================
    # waves - Pick wave groupings
    # =========================================================================
    op.create_table(
        "waves",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("facility_id", sa.String(50), nullable=False),
        sa.Column("wave_number", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
            comment="DRAFT, RELEASED, IN_PROGRESS, COMPLETE",
        ),
        sa.Column(
            "total_orders", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "total_lines", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "total_units", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("released_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_waves_facility_id", "waves", ["facility_id"], schema=SCHEMA)
    op.create_index("ix_waves_wave_number", "waves", ["wave_number"], schema=SCHEMA)
    op.create_index("ix_waves_status", "waves", ["status"], schema=SCHEMA)

    # =========================================================================
    # tasks - Warehouse tasks (pick, putaway, etc.)
    # =========================================================================
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("facility_id", sa.String(50), nullable=False),
        sa.Column(
            "wave_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.waves.id"),
            nullable=True,
        ),
        sa.Column(
            "task_type",
            sa.String(20),
            nullable=False,
            comment="PICK, PUTAWAY, RECEIVE, CYCLE_COUNT, REPLENISH",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
            comment="PENDING, ASSIGNED, IN_PROGRESS, COMPLETE, CANCELLED",
        ),
        sa.Column(
            "from_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.locations.id"),
            nullable=True,
        ),
        sa.Column(
            "to_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.locations.id"),
            nullable=True,
        ),
        sa.Column(
            "sku_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.skus.id"),
            nullable=False,
        ),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("assigned_to", sa.String(100), nullable=True),
        sa.Column(
            "priority", sa.Integer(), nullable=False, server_default=sa.text("5")
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_tasks_facility_id", "tasks", ["facility_id"], schema=SCHEMA)
    op.create_index("ix_tasks_wave_id", "tasks", ["wave_id"], schema=SCHEMA)
    op.create_index("ix_tasks_task_type", "tasks", ["task_type"], schema=SCHEMA)
    op.create_index("ix_tasks_status", "tasks", ["status"], schema=SCHEMA)
    op.create_index("ix_tasks_sku_id", "tasks", ["sku_id"], schema=SCHEMA)
    op.create_index(
        "ix_tasks_from_location_id", "tasks", ["from_location_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_tasks_to_location_id", "tasks", ["to_location_id"], schema=SCHEMA
    )
    op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"], schema=SCHEMA)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], schema=SCHEMA)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("tasks", schema=SCHEMA)
    op.drop_table("waves", schema=SCHEMA)
    op.drop_table("order_lines", schema=SCHEMA)
    op.drop_table("orders", schema=SCHEMA)
    op.drop_table("inventory_movements", schema=SCHEMA)
    op.drop_table("inventory_positions", schema=SCHEMA)
    op.drop_table("skus", schema=SCHEMA)
    op.drop_table("locations", schema=SCHEMA)

    # Drop schema
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
