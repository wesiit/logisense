"""Tests for License Service endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from jose import jwt

from app.config import Settings
from app.models import License


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "license-service"


class TestIssueLicense:
    """Tests for license issuance endpoint."""

    def test_issue_license_success(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
        settings: Settings,
    ) -> None:
        """Test successful license issuance."""
        # Mock database to return no existing license
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/v1/license/issue",
            json={
                "tenant_id": "tenant-001",
                "tenant_name": "Test Company",
                "licensed_modules": ["iwms", "lip", "ccvp"],
                "facility_count": 5,
                "tier": "enterprise",
                "valid_days": 365,
            },
            headers={"X-Master-Key": "test-master-api-key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "license_token" in data
        assert data["licensed_modules"] == ["iwms", "lip", "ccvp"]
        assert "expires_at" in data

        # Verify the JWT token
        token = data["license_token"]
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["tenant_id"] == "tenant-001"
        assert payload["tenant_name"] == "Test Company"
        assert payload["licensed_modules"] == ["iwms", "lip", "ccvp"]
        assert payload["facility_count"] == 5
        assert payload["tier"] == "enterprise"

    def test_issue_license_without_master_key(self, client: TestClient) -> None:
        """Test license issuance fails without master API key."""
        response = client.post(
            "/v1/license/issue",
            json={
                "tenant_id": "tenant-001",
                "tenant_name": "Test Company",
                "licensed_modules": ["iwms"],
                "facility_count": 1,
                "tier": "standard",
                "valid_days": 365,
            },
        )
        assert response.status_code == 403

    def test_issue_license_invalid_master_key(self, client: TestClient) -> None:
        """Test license issuance fails with invalid master API key."""
        response = client.post(
            "/v1/license/issue",
            json={
                "tenant_id": "tenant-001",
                "tenant_name": "Test Company",
                "licensed_modules": ["iwms"],
                "facility_count": 1,
                "tier": "standard",
                "valid_days": 365,
            },
            headers={"X-Master-Key": "wrong-key"},
        )
        assert response.status_code == 403


class TestValidateLicense:
    """Tests for license validation endpoint."""

    def test_validate_valid_license(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
        sample_license: License,
        settings: Settings,
    ) -> None:
        """Test validation of a valid license token."""
        # Create a valid token
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": sample_license.tenant_id,
                "tenant_id": sample_license.tenant_id,
                "tenant_name": sample_license.tenant_name,
                "licensed_modules": sample_license.licensed_modules,
                "facility_count": sample_license.facility_count,
                "tier": sample_license.tier,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=365)).timestamp()),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Update sample_license with token hash
        import hashlib

        sample_license.token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Mock database to return the license
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_license
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/v1/license/validate",
            json={
                "token": token,
                "module_id": "iwms",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["tenant_id"] == "tenant-001"
        assert "iwms" in data["licensed_modules"]
        assert data["facility_count"] == 5

    def test_validate_wrong_module(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
        sample_license: License,
        settings: Settings,
    ) -> None:
        """Test validation fails for unlicensed module."""
        # Create a valid token
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": sample_license.tenant_id,
                "tenant_id": sample_license.tenant_id,
                "tenant_name": sample_license.tenant_name,
                "licensed_modules": sample_license.licensed_modules,  # iwms, lip, ccvp
                "facility_count": sample_license.facility_count,
                "tier": sample_license.tier,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=365)).timestamp()),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Update sample_license with token hash
        import hashlib

        sample_license.token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Mock database to return the license
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_license
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Request validation for a module NOT in the license (pise is not licensed)
        response = client.post(
            "/v1/license/validate",
            json={
                "token": token,
                "module_id": "pise",  # Not in licensed_modules
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["tenant_id"] == "tenant-001"
        assert "pise" not in data["licensed_modules"]
        assert "not licensed" in data["message"].lower()

    def test_validate_expired_license(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
        expired_license: License,
        settings: Settings,
    ) -> None:
        """Test validation fails for expired license token."""
        # Create an expired token
        now = datetime.now(UTC)
        expired_time = now - timedelta(days=1)
        token = jwt.encode(
            {
                "sub": expired_license.tenant_id,
                "tenant_id": expired_license.tenant_id,
                "tenant_name": expired_license.tenant_name,
                "licensed_modules": expired_license.licensed_modules,
                "facility_count": expired_license.facility_count,
                "tier": expired_license.tier,
                "iat": int((now - timedelta(days=400)).timestamp()),
                "exp": int(expired_time.timestamp()),  # Expired
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = client.post(
            "/v1/license/validate",
            json={
                "token": token,
                "module_id": "iwms",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "expired" in data["message"].lower() or "invalid" in data["message"].lower()

    def test_validate_invalid_token(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test validation fails for invalid token."""
        response = client.post(
            "/v1/license/validate",
            json={
                "token": "invalid.token.here",
                "module_id": "iwms",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "invalid" in data["message"].lower()

    def test_validate_revoked_license(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
        sample_license: License,
        settings: Settings,
    ) -> None:
        """Test validation fails for revoked license."""
        # Create a valid token
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": sample_license.tenant_id,
                "tenant_id": sample_license.tenant_id,
                "tenant_name": sample_license.tenant_name,
                "licensed_modules": sample_license.licensed_modules,
                "facility_count": sample_license.facility_count,
                "tier": sample_license.tier,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=365)).timestamp()),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Mark license as revoked
        sample_license.is_active = False

        # Mock database to return the revoked license
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_license
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/v1/license/validate",
            json={
                "token": token,
                "module_id": "iwms",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "revoked" in data["message"].lower()


class TestGetLicense:
    """Tests for get license endpoint."""

    def test_get_license_success(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
        sample_license: License,
    ) -> None:
        """Test getting license details for a tenant."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_license
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = client.get("/v1/license/tenant-001")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-001"
        assert data["tenant_name"] == "Test Company"
        assert data["licensed_modules"] == ["iwms", "lip", "ccvp"]
        assert data["facility_count"] == 5
        assert data["tier"] == "enterprise"
        assert data["is_active"] is True

    def test_get_license_not_found(
        self,
        client: TestClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test getting license for non-existent tenant."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = client.get("/v1/license/non-existent-tenant")

        assert response.status_code == 404
