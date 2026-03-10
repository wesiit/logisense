"""Tests for inventory endpoints."""

from uuid import uuid4

import pytest
from api.models import SKU, InventoryPosition, Location
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from .conftest import SAMPLE_FACILITY_ID


class TestInventoryPositions:
    """Tests for inventory position endpoints."""

    @pytest.mark.asyncio
    async def test_get_inventory_empty_facility(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting inventory for a facility with no positions."""
        response = await async_client.get(
            "/v1/iwms/inventory/positions",
            params={"facility_id": SAMPLE_FACILITY_ID},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_get_inventory_by_location(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_location: Location,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test filtering inventory by location."""
        # Create inventory position
        position = InventoryPosition(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_id=sample_location.id,
            sku_id=sample_sku.id,
            quantity=100,
            quantity_reserved=0,
        )
        test_db.add(position)
        await test_db.flush()

        # Get inventory filtered by location
        response = await async_client.get(
            "/v1/iwms/inventory/positions",
            params={
                "facility_id": SAMPLE_FACILITY_ID,
                "location_id": str(sample_location.id),
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["location_id"] == str(sample_location.id)
        assert data["items"][0]["quantity"] == 100


class TestInventoryMovements:
    """Tests for inventory movement endpoints."""

    @pytest.mark.asyncio
    async def test_create_inventory_movement_receive(
        self,
        async_client: AsyncClient,
        sample_location: Location,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a receive movement."""
        movement_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "movement_type": "RECEIVE",
            "sku_id": str(sample_sku.id),
            "quantity": 50,
            "to_location_id": str(sample_location.id),
            "reference_id": "PO-001",
            "reference_type": "PURCHASE_ORDER",
        }

        response = await async_client.post(
            "/v1/iwms/inventory/movements",
            json=movement_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["movement_type"] == "RECEIVE"
        assert data["quantity"] == 50
        assert data["sku_id"] == str(sample_sku.id)

    @pytest.mark.asyncio
    async def test_inventory_position_updated_after_movement(
        self,
        async_client: AsyncClient,
        sample_location: Location,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that inventory position is created/updated after movement."""
        # Create receive movement
        movement_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "movement_type": "RECEIVE",
            "sku_id": str(sample_sku.id),
            "quantity": 100,
            "to_location_id": str(sample_location.id),
        }

        response = await async_client.post(
            "/v1/iwms/inventory/movements",
            json=movement_data,
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Check inventory position was created
        response = await async_client.get(
            "/v1/iwms/inventory/positions",
            params={
                "facility_id": SAMPLE_FACILITY_ID,
                "sku_id": str(sample_sku.id),
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Find position at our location
        positions = [
            p for p in data["items"] if p["location_id"] == str(sample_location.id)
        ]
        assert len(positions) == 1
        assert positions[0]["quantity"] == 100

    @pytest.mark.asyncio
    async def test_inventory_movement_pick_reduces_quantity(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_location: Location,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that pick movement reduces inventory quantity."""
        # First create inventory position with stock
        position = InventoryPosition(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_id=sample_location.id,
            sku_id=sample_sku.id,
            quantity=100,
            quantity_reserved=0,
        )
        test_db.add(position)
        await test_db.flush()

        # Create pick movement
        movement_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "movement_type": "PICK",
            "sku_id": str(sample_sku.id),
            "quantity": 30,
            "from_location_id": str(sample_location.id),
        }

        response = await async_client.post(
            "/v1/iwms/inventory/movements",
            json=movement_data,
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Check inventory was reduced
        response = await async_client.get(
            "/v1/iwms/inventory/positions",
            params={
                "facility_id": SAMPLE_FACILITY_ID,
                "location_id": str(sample_location.id),
            },
            headers=auth_headers,
        )

        data = response.json()
        assert data["total"] >= 1
        # Quantity should be reduced by 30
        position_data = data["items"][0]
        assert position_data["quantity"] == 70

    @pytest.mark.asyncio
    async def test_movement_transfer_between_locations(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test transfer movement between locations."""
        # Create two locations
        from_location = Location(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_code=f"FROM-{uuid4().hex[:8]}",
            location_type="STORAGE",
            is_active=True,
        )
        to_location = Location(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_code=f"TO-{uuid4().hex[:8]}",
            location_type="PICK",
            is_active=True,
        )
        test_db.add(from_location)
        test_db.add(to_location)
        await test_db.flush()

        # Create inventory at source
        position = InventoryPosition(
            id=uuid4(),
            facility_id=SAMPLE_FACILITY_ID,
            location_id=from_location.id,
            sku_id=sample_sku.id,
            quantity=50,
            quantity_reserved=0,
        )
        test_db.add(position)
        await test_db.flush()

        # Transfer
        movement_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "movement_type": "TRANSFER",
            "sku_id": str(sample_sku.id),
            "quantity": 20,
            "from_location_id": str(from_location.id),
            "to_location_id": str(to_location.id),
        }

        response = await async_client.post(
            "/v1/iwms/inventory/movements",
            json=movement_data,
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Verify source reduced
        response = await async_client.get(
            "/v1/iwms/inventory/positions",
            params={
                "facility_id": SAMPLE_FACILITY_ID,
                "location_id": str(from_location.id),
            },
            headers=auth_headers,
        )
        data = response.json()
        assert data["items"][0]["quantity"] == 30

        # Verify destination has inventory
        response = await async_client.get(
            "/v1/iwms/inventory/positions",
            params={
                "facility_id": SAMPLE_FACILITY_ID,
                "location_id": str(to_location.id),
            },
            headers=auth_headers,
        )
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["quantity"] == 20


class TestLocations:
    """Tests for location endpoints."""

    @pytest.mark.asyncio
    async def test_create_location(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a new location."""
        location_data = {
            "facility_id": SAMPLE_FACILITY_ID,
            "zone_id": "ZONE-B",
            "aisle": "B",
            "bay": "02",
            "level": "2",
            "bin": "001",
            "location_code": f"LOC-NEW-{uuid4().hex[:8]}",
            "location_type": "STORAGE",
            "max_weight_kg": 500,
            "is_active": True,
        }

        response = await async_client.post(
            "/v1/iwms/inventory/locations",
            json=location_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["location_code"] == location_data["location_code"]
        assert data["zone_id"] == "ZONE-B"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_locations(
        self,
        async_client: AsyncClient,
        sample_location: Location,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing locations."""
        response = await async_client.get(
            "/v1/iwms/inventory/locations",
            params={"facility_id": SAMPLE_FACILITY_ID},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(loc["id"] == str(sample_location.id) for loc in data["items"])


class TestSKUs:
    """Tests for SKU endpoints."""

    @pytest.mark.asyncio
    async def test_create_sku(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a new SKU."""
        sku_data = {
            "sku_code": f"SKU-NEW-{uuid4().hex[:8]}",
            "sku_name": "New Test Product",
            "category_l1": "Food",
            "category_l2": "Snacks",
            "unit_of_measure": "CS",
            "weight_kg": 2.5,
            "is_perishable": True,
            "temperature_zone": "AMBIENT",
            "reorder_point": 50,
            "min_order_qty": 5,
        }

        response = await async_client.post(
            "/v1/iwms/inventory/skus",
            json=sku_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["sku_code"] == sku_data["sku_code"]
        assert data["is_perishable"] is True

    @pytest.mark.asyncio
    async def test_list_skus(
        self,
        async_client: AsyncClient,
        sample_sku: SKU,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing SKUs."""
        response = await async_client.get(
            "/v1/iwms/inventory/skus",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
