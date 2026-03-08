"""Pytest fixtures for License Service tests."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.main import app
from app.models import License, get_db_session


def get_test_settings() -> Settings:
    """Get test settings with predictable values."""
    # pragma: allowlist nextline secret
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",  # pragma: allowlist secret
        jwt_secret_key="test-jwt-secret-key",  # pragma: allowlist secret
        jwt_algorithm="HS256",
        master_api_key="test-master-api-key",  # pragma: allowlist secret
    )


@pytest.fixture
def settings() -> Settings:
    """Provide test settings."""
    return get_test_settings()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def sample_license() -> License:
    """Create a sample license for testing."""
    now = datetime.now(UTC)
    return License(
        id="test-license-id",
        tenant_id="tenant-001",
        tenant_name="Test Company",
        licensed_modules=["iwms", "lip", "ccvp"],
        facility_count=5,
        tier="enterprise",
        issued_at=now,
        expires_at=now + timedelta(days=365),
        is_active=True,
        token_hash=None,
    )


@pytest.fixture
def expired_license() -> License:
    """Create an expired license for testing."""
    now = datetime.now(UTC)
    return License(
        id="expired-license-id",
        tenant_id="tenant-expired",
        tenant_name="Expired Company",
        licensed_modules=["iwms"],
        facility_count=1,
        tier="starter",
        issued_at=now - timedelta(days=400),
        expires_at=now - timedelta(days=35),
        is_active=True,
        token_hash=None,
    )


@pytest.fixture
def client(mock_db_session: AsyncMock, settings: Settings) -> TestClient:
    """Create a test client with mocked dependencies."""
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(
    mock_db_session: AsyncMock,
    settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
