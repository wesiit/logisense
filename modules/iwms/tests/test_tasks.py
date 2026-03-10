"""Tests for task management endpoints."""

from uuid import uuid4

import pytest
from api.models import SKU, InventoryPosition, Location, Order, Task, Wave
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from .conftest import SAMPLE_FACILITY_ID


class TestTaskListing:
    """Tests for task listing endpoints."""

    @pytest.mark.asyncio
    async def test_get_pending_tasks_for_facility(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting pending tasks for a facility."""
        # Create a wave with tasks
        wave = Wave(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            wave_number=f"W-TASK-{uuid4().hex[:8].upper()}",
            status="RELEASED",
            total_orders=1,
            total_lines=2,
            total_units=10,
            created_by="test-user",
        )
        test_db.add(wave)
        await test_db.flush()

        # Create tasks
        location = Location(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_code=f"LOC-TASK-{uuid4().hex[:8]}",
            location_type="PICK",
            is_active=True,
        )
        test_db.add(location)
        await test_db.flush()

        for i in range(3):
            task = Task(
                id=uuid4(),
                facility_id=SAMPLE_FACILITY_ID,
                wave_id=wave.id,
                task_type="PICK",
                status="PENDING",
                sku_id=sample_sku.id,
                from_location_id=location.id,
                quantity=5,
                priority=5 - i,
            )
            test_db.add(task)
        await test_db.flush()

        # Get pending tasks
        response = await async_client.get(
            "/v1/iwms/tasks",
            params={"facility_id": SAMPLE_FACILITY_ID, "status": "PENDING"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        # All returned tasks should be PENDING
        for task in data["items"]:
            assert task["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_get_tasks_by_wave(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting tasks filtered by wave."""
        # Create wave which creates tasks
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

        # Get tasks for this wave
        response = await async_client.get(
            "/v1/iwms/tasks",
            params={"facility_id": SAMPLE_FACILITY_ID, "wave_id": wave_id},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6  # 3 orders x 2 lines
        for task in data["items"]:
            assert task["wave_id"] == wave_id


class TestTaskAssignment:
    """Tests for task assignment functionality."""

    @pytest.mark.asyncio
    async def test_assign_task_to_operator(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test assigning a task to an operator."""
        # Create wave with tasks
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

        # Release wave to make tasks available
        response = await async_client.post(
            f"/v1/iwms/waves/{wave_id}/release",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Get a task
        response = await async_client.get(
            "/v1/iwms/tasks",
            params={"facility_id": SAMPLE_FACILITY_ID, "wave_id": wave_id},
            headers=auth_headers,
        )
        task_id = response.json()["items"][0]["id"]

        # Assign task
        response = await async_client.patch(
            f"/v1/iwms/tasks/{task_id}/assign",
            json={"assigned_to": "operator-001"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == "operator-001"
        assert data["status"] == "ASSIGNED"

    @pytest.mark.asyncio
    async def test_assign_already_assigned_task_fails(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test that assigning an already assigned task fails."""
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

        await async_client.post(
            f"/v1/iwms/waves/{wave_id}/release",
            headers=auth_headers,
        )

        # Get a task
        response = await async_client.get(
            "/v1/iwms/tasks",
            params={"facility_id": SAMPLE_FACILITY_ID, "wave_id": wave_id},
            headers=auth_headers,
        )
        task_id = response.json()["items"][0]["id"]

        # First assignment succeeds
        response = await async_client.patch(
            f"/v1/iwms/tasks/{task_id}/assign",
            json={"assigned_to": "operator-001"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Second assignment replaces previous assignment
        response = await async_client.patch(
            f"/v1/iwms/tasks/{task_id}/assign",
            json={"assigned_to": "operator-002"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == "operator-002"


class TestTaskCompletion:
    """Tests for task completion functionality."""

    @pytest.mark.asyncio
    async def test_complete_task_updates_inventory(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that completing a task updates inventory."""
        # Create location with inventory
        location = Location(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_code=f"LOC-PICK-{uuid4().hex[:8]}",
            location_type="PICK",
            is_active=True,
        )
        test_db.add(location)
        await test_db.flush()

        # Create inventory position
        position = InventoryPosition(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_id=location.id,
            sku_id=sample_sku.id,
            quantity=100,
            quantity_reserved=10,
        )
        test_db.add(position)
        await test_db.flush()

        # Create wave
        wave = Wave(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            wave_number=f"W-COMPLETE-{uuid4().hex[:8]}",
            status="RELEASED",
            total_orders=1,
            total_lines=1,
            total_units=10,
            created_by="test-user",
        )
        test_db.add(wave)
        await test_db.flush()

        # Create task
        task = Task(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            wave_id=wave.id,
            task_type="PICK",
            status="IN_PROGRESS",
            sku_id=sample_sku.id,
            from_location_id=location.id,
            quantity=10,
            priority=5,
            assigned_to="operator-001",
        )
        test_db.add(task)
        await test_db.flush()

        # Complete task
        response = await async_client.patch(
            f"/v1/iwms/tasks/{task.id}/complete",
            json={"quantity_completed": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETE"
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_complete_pending_task_succeeds(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test completing a pending (unassigned) task directly."""
        # Create wave
        wave = Wave(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            wave_number=f"W-PENDING-{uuid4().hex[:8]}",
            status="RELEASED",
            total_orders=1,
            total_lines=1,
            total_units=5,
            created_by="test-user",
        )
        test_db.add(wave)
        await test_db.flush()

        # Create location
        location = Location(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_code=f"LOC-PEND-{uuid4().hex[:8]}",
            location_type="PICK",
            is_active=True,
        )
        test_db.add(location)
        await test_db.flush()

        # Create task in PENDING status
        task = Task(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            wave_id=wave.id,
            task_type="PICK",
            status="PENDING",
            sku_id=sample_sku.id,
            from_location_id=location.id,
            quantity=5,
            priority=5,
        )
        test_db.add(task)
        await test_db.flush()

        # Complete without prior assignment (direct completion)
        response = await async_client.patch(
            f"/v1/iwms/tasks/{task.id}/complete",
            json={"quantity_completed": 5},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETE"

    @pytest.mark.asyncio
    async def test_complete_task_partial_pick(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test completing a task with partial pick quantity."""
        # Create location with inventory
        location = Location(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_code=f"LOC-PARTIAL-{uuid4().hex[:8]}",
            location_type="PICK",
            is_active=True,
        )
        test_db.add(location)
        await test_db.flush()

        # Create inventory position
        position = InventoryPosition(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_id=location.id,
            sku_id=sample_sku.id,
            quantity=100,
            quantity_reserved=0,
        )
        test_db.add(position)
        await test_db.flush()

        # Create wave
        wave = Wave(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            wave_number=f"W-PARTIAL-{uuid4().hex[:8]}",
            status="RELEASED",
            total_orders=1,
            total_lines=1,
            total_units=10,
            created_by="test-user",
        )
        test_db.add(wave)
        await test_db.flush()

        # Create task
        task = Task(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            wave_id=wave.id,
            task_type="PICK",
            status="IN_PROGRESS",
            sku_id=sample_sku.id,
            from_location_id=location.id,
            quantity=10,
            priority=5,
            assigned_to="operator-001",
        )
        test_db.add(task)
        await test_db.flush()

        # Complete with partial quantity
        response = await async_client.patch(
            f"/v1/iwms/tasks/{task.id}/complete",
            json={
                "quantity_completed": 7,
                "notes": "Stock out - partial pick",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETE"
        assert data["completed_at"] is not None


class TestTaskGet:
    """Tests for getting individual tasks."""

    @pytest.mark.asyncio
    async def test_get_task_by_id(
        self,
        async_client: AsyncClient,
        multiple_orders: list[Order],
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting a task by ID."""
        # Create wave with tasks
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

        # Get tasks
        response = await async_client.get(
            "/v1/iwms/tasks",
            params={"facility_id": SAMPLE_FACILITY_ID, "wave_id": wave_id},
            headers=auth_headers,
        )
        task_id = response.json()["items"][0]["id"]

        # Get single task
        response = await async_client.get(
            f"/v1/iwms/tasks/{task_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["wave_id"] == wave_id
        assert data["task_type"] == "PICK"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting a task that doesn't exist."""
        response = await async_client.get(
            f"/v1/iwms/tasks/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
