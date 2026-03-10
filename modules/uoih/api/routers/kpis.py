"""KPI endpoints for UOIH API."""

from datetime import date

import structlog
from fastapi import APIRouter, HTTPException, Query

from ..schemas import (
    DailyKPI,
    DailyKPIResponse,
    InventoryAccuracyPoint,
    InventoryAccuracyResponse,
)
from ..services.iceberg_client import get_iceberg_client

router = APIRouter(prefix="/kpis", tags=["KPIs"])
logger = structlog.get_logger()


@router.get("/daily", response_model=DailyKPIResponse)
async def get_daily_kpis(
    facility_id: str = Query(..., description="Facility identifier"),
    date_from: date = Query(..., description="Start date (inclusive)"),
    date_to: date = Query(..., description="End date (inclusive)"),
) -> DailyKPIResponse:
    """
    Get daily KPI metrics for a facility.

    Returns aggregated KPIs including:
    - total_movements: Count of all inventory movements
    - picks_completed: Count of PICK type movements
    - inventory_accuracy_pct: Cycle count accuracy percentage
    - orders_fulfilled: Distinct orders in DISPATCHED status
    """
    if date_from > date_to:
        raise HTTPException(
            status_code=400, detail="date_from must be before or equal to date_to"
        )

    if (date_to - date_from).days > 365:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")

    try:
        client = get_iceberg_client()
        raw_kpis = await client.get_daily_kpis(facility_id, date_from, date_to)

        kpis = [
            DailyKPI(
                facility_id=row["facility_id"],
                date=row["date"],
                total_movements=row.get("total_movements", 0),
                picks_completed=row.get("picks_completed", 0),
                inventory_accuracy_pct=row.get("inventory_accuracy_pct", 0.0),
                orders_fulfilled=row.get("orders_fulfilled", 0),
            )
            for row in raw_kpis
        ]

        return DailyKPIResponse(
            facility_id=facility_id,
            date_from=date_from,
            date_to=date_to,
            kpis=kpis,
        )

    except RuntimeError as e:
        if "not initialized" in str(e):
            raise HTTPException(status_code=503, detail="Iceberg catalog unavailable")
        raise

    except Exception as e:
        logger.error("get_daily_kpis_failed", facility_id=facility_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve KPIs")


@router.get("/inventory-accuracy", response_model=InventoryAccuracyResponse)
async def get_inventory_accuracy(
    facility_id: str = Query(..., description="Facility identifier"),
) -> InventoryAccuracyResponse:
    """
    Get 30-day inventory accuracy trend for a facility.

    Returns daily accuracy percentages based on cycle count results.
    """
    try:
        client = get_iceberg_client()
        raw_data = await client.get_inventory_accuracy_trend(facility_id, days=30)

        trend = [
            InventoryAccuracyPoint(
                date=row["date"],
                accuracy_pct=row.get("inventory_accuracy_pct", 0.0),
                cycle_counts=row.get("cycle_counts", 0),
            )
            for row in raw_data
        ]

        # Calculate weighted average
        total_counts = sum(p.cycle_counts for p in trend)
        if total_counts > 0:
            avg_accuracy = (
                sum(p.accuracy_pct * p.cycle_counts for p in trend) / total_counts
            )
        else:
            avg_accuracy = 0.0

        return InventoryAccuracyResponse(
            facility_id=facility_id,
            period_days=30,
            trend=sorted(trend, key=lambda x: x.date),
            average_accuracy_pct=round(avg_accuracy, 2),
        )

    except RuntimeError as e:
        if "not initialized" in str(e):
            raise HTTPException(status_code=503, detail="Iceberg catalog unavailable")
        raise

    except Exception as e:
        logger.error(
            "get_inventory_accuracy_failed", facility_id=facility_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve inventory accuracy"
        )
