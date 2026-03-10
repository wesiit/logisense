"""Pytest fixtures for iWMS API tests."""

import os
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["TEST_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from api.config import get_settings
from api.db import Base, get_db_session
from api.main import create_app
from api.models import SKU, Location, Order, OrderLine, Wave
from api.services.kafka_producer import close_kafka_producer, init_kafka_producer

# Test constants
SAMPLE_FACILITY_ID = "FACILITY_TEST_001"


@pytest.fixture(scope="session")
def sample_facility_id() -> str:
    """Return sample facility ID for tests."""
    return SAMPLE_FACILITY_ID


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return authorization headers for test requests."""
    return {"Authorization": "Bearer test-dev-token"}


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh test database for each test."""
    # Create async engine with SQLite
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing the API."""
    app = create_app()

    # Initialize Kafka producer for tests (uses mock in TEST_MODE)
    settings = get_settings()
    await init_kafka_producer(settings)

    # Override database dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        try:
            yield test_db
            await test_db.commit()
        except Exception:
            await test_db.rollback()
            raise

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup Kafka producer
    await close_kafka_producer()


@pytest_asyncio.fixture
async def sample_location(test_db: AsyncSession) -> Location:
    """Create a sample location for testing."""
    location = Location(
        id=uuid4(),
        facility_id=SAMPLE_FACILITY_ID,
        zone_id="ZONE-A",
        aisle="A",
        bay="01",
        level="1",
        bin="001",
        location_code=f"LOC-{uuid4().hex[:8].upper()}",
        location_type="PICK",
        max_weight_kg=100.0,
        is_active=True,
    )
    test_db.add(location)
    await test_db.flush()
    await test_db.refresh(location)
    return location


@pytest_asyncio.fixture
async def sample_sku(test_db: AsyncSession) -> SKU:
    """Create a sample SKU for testing."""
    sku = SKU(
        id=uuid4(),
        sku_code=f"SKU-{uuid4().hex[:8].upper()}",
        sku_name="Test Product",
        category_l1="Electronics",
        category_l2="Gadgets",
        unit_of_measure="EA",
        weight_kg=0.5,
        is_perishable=False,
        reorder_point=10,
        min_order_qty=1,
        is_active=True,
    )
    test_db.add(sku)
    await test_db.flush()
    await test_db.refresh(sku)
    return sku


@pytest_asyncio.fixture
async def sample_order(
    test_db: AsyncSession,
    sample_sku: SKU,
) -> Order:
    """Create a sample order with lines for testing."""
    order = Order(
        id=uuid4(),
        facility_id=SAMPLE_FACILITY_ID,
        order_number=f"ORD-{uuid4().hex[:8].upper()}",
        order_type="OUTBOUND",
        status="PENDING",
        priority=5,
        customer_id="CUST-001",
    )
    test_db.add(order)
    await test_db.flush()

    # Add order line
    line = OrderLine(
        id=uuid4(),
        order_id=order.id,
        sku_id=sample_sku.id,
        quantity_ordered=10,
        quantity_picked=0,
        status="PENDING",
    )
    test_db.add(line)
    await test_db.flush()
    await test_db.refresh(order)

    return order


@pytest_asyncio.fixture
async def multiple_orders(
    test_db: AsyncSession,
    sample_sku: SKU,
) -> list[Order]:
    """Create multiple orders for wave testing."""
    orders = []
    for i in range(3):
        order = Order(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            order_number=f"ORD-WAVE-{i:03d}-{uuid4().hex[:4].upper()}",
            order_type="OUTBOUND",
            status="PENDING",
            priority=5,
            customer_id=f"CUST-{i:03d}",
        )
        test_db.add(order)
        await test_db.flush()

        # Add 2 lines per order
        for j in range(2):
            line = OrderLine(
                id=uuid4(),
                order_id=order.id,
                sku_id=sample_sku.id,
                quantity_ordered=5 + j,
                quantity_picked=0,
                status="PENDING",
            )
            test_db.add(line)

        await test_db.flush()
        await test_db.refresh(order)
        orders.append(order)

    return orders


@pytest_asyncio.fixture
async def sample_wave(
    test_db: AsyncSession,
) -> Wave:
    """Create a sample wave for testing."""
    wave = Wave(
        id=uuid4(),
        facility_id=SAMPLE_FACILITY_ID,
        wave_number=f"W-TEST-{uuid4().hex[:8].upper()}",
        status="DRAFT",
        total_orders=0,
        total_lines=0,
        total_units=0,
        created_by="test-user",
    )
    test_db.add(wave)
    await test_db.flush()
    await test_db.refresh(wave)
    return wave
