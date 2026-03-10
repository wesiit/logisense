"""Tests for wave management endpoints."""

from uuid import uuid4

import pytest
from api.models import Order
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from .conftest import SAMPLE_FACILITY_ID


class TestWaveCreation:
    """Tests for wave creation."""

    @pytest.mark.asyncio
    async def test_create_wave_from_orders(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a wave from multiple orders."""
        order_ids = [str(order.id) for order in multiple_orders]

        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "DRAFT"
        assert data["facility_id"] == SAMPLE_FACILITY_ID
        assert data["total_orders"] == 3
        assert data["total_lines"] == 6  # 3 orders x 2 lines each
        assert "wave_number" in data

    @pytest.mark.asyncio
    async def test_wave_creates_correct_task_count(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test that wave creation creates correct number of tasks."""
        order_ids = [str(order.id) for order in multiple_orders]

        # Create wave
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        wave_id = response.json()["id"]

        # Get wave with tasks
        response = await async_client.get(
            f"/v1/iwms/waves/{wave_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have 6 tasks (one per order line)
        assert data["task_count"] == 6
        assert len(data["tasks"]) == 6

        # All tasks should be PICK type and PENDING status
        for task in data["tasks"]:
            assert task["task_type"] == "PICK"
            assert task["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_create_wave_no_orders_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that creating a wave with no valid orders fails."""
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": [str(uuid4())],  # Non-existent order
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "No pending orders found" in response.json()["detail"]


class TestWaveRelease:
    """Tests for wave release functionality."""

    @pytest.mark.asyncio
    async def test_release_wave_changes_status(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test that releasing a wave changes its status."""
        # Create wave
        order_ids = [str(order.id) for order in multiple_orders]
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        wave_id = response.json()["id"]

        # Release wave
        response = await async_client.post(
            f"/v1/iwms/waves/{wave_id}/release",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RELEASED"
        assert data["released_at"] is not None
        assert data["task_count"] == 6

    @pytest.mark.asyncio
    async def test_released_wave_cannot_be_released_again(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test that a released wave cannot be released again."""
        # Create and release wave
        order_ids = [str(order.id) for order in multiple_orders]
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )
        wave_id = response.json()["id"]

        # First release
        response = await async_client.post(
            f"/v1/iwms/waves/{wave_id}/release",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Try to release again
        response = await async_client.post(
            f"/v1/iwms/waves/{wave_id}/release",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Cannot release wave" in response.json()["detail"]


class TestWaveCompletion:
    """Tests for wave completion."""

    @pytest.mark.asyncio
    async def test_complete_wave(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test completing a wave."""
        # Create and release wave
        order_ids = [str(order.id) for order in multiple_orders]
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )
        wave_id = response.json()["id"]

        # Release
        response = await async_client.post(
            f"/v1/iwms/waves/{wave_id}/release",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Complete wave
        response = await async_client.post(
            f"/v1/iwms/waves/{wave_id}/complete",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETE"
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_draft_wave_cannot_be_completed(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test that a draft wave cannot be completed directly."""
        # Create wave (stays in DRAFT)
        order_ids = [str(order.id) for order in multiple_orders]
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )
        wave_id = response.json()["id"]

        # Try to complete without releasing
        response = await async_client.post(
            f"/v1/iwms/waves/{wave_id}/complete",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Cannot complete wave" in response.json()["detail"]


class TestWaveProgress:
    """Tests for wave progress tracking."""

    @pytest.mark.asyncio
    async def test_get_wave_progress(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting wave progress statistics."""
        # Create and release wave
        order_ids = [str(order.id) for order in multiple_orders]
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )
        wave_id = response.json()["id"]

        # Get progress
        response = await async_client.get(
            f"/v1/iwms/waves/{wave_id}/progress",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["wave_id"] == wave_id
        assert data["total_tasks"] == 6
        assert data["pending_tasks"] == 6
        assert data["completed_tasks"] == 0
        assert data["completion_percentage"] == 0


class TestWaveList:
    """Tests for wave listing."""

    @pytest.mark.asyncio
    async def test_list_waves(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing waves."""
        # Create a wave
        order_ids = [str(order.id) for order in multiple_orders]
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )

        # List waves
        response = await async_client.get(
            "/v1/iwms/waves",
            params={"facility_id": SAMPLE_FACILITY_ID},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_waves_filter_by_status(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test filtering waves by status."""
        # Create and release a wave
        order_ids = [str(order.id) for order in multiple_orders]
        wave_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "order_ids": order_ids,
        }

        response = await async_client.post(
            "/v1/iwms/waves",
            json=wave_data,
            headers=auth_headers,
        )
        wave_id = response.json()["id"]

        await async_client.post(
            f"/v1/iwms/waves/{wave_id}/release",
            headers=auth_headers,
        )

        # Filter by RELEASED status
        response = await async_client.get(
            "/v1/iwms/waves",
            params={"facility_id": SAMPLE_FACILITY_ID, "status": "RELEASED"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert all(w["status"] == "RELEASED" for w in data["items"])
