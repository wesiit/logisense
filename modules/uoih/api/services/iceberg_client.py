"""Iceberg client for reading gold layer tables."""

from datetime import date
from typing import Any

import pyarrow as pa
import structlog
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import And, EqualTo, GreaterThanOrEqual, LessThanOrEqual

from ..config import Settings

logger = structlog.get_logger()


class IcebergClient:
    """Client for querying Iceberg tables."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._catalog = None

    def _get_catalog(self):
        """Lazy load Iceberg catalog."""
        if self._catalog is None:
            self._catalog = load_catalog(
                "logisense",
                **{
                    "type": "rest",
                    "uri": self.settings.ICEBERG_CATALOG_URI,
                    "s3.endpoint": self.settings.MINIO_ENDPOINT,
                    "s3.access-key-id": self.settings.MINIO_ACCESS_KEY,
                    "s3.secret-access-key": self.settings.MINIO_SECRET_KEY,
                    "s3.path-style-access": "true",
                },
            )
        return self._catalog

    async def get_daily_kpis(
        self, facility_id: str, date_from: date, date_to: date
    ) -> list[dict[str, Any]]:
        """Fetch daily KPIs from gold.dc_daily_kpis table."""
        try:
            catalog = self._get_catalog()
            table = catalog.load_table("gold.dc_daily_kpis")

            # Build filter expression
            filter_expr = And(
                EqualTo("facility_id", facility_id),
                GreaterThanOrEqual("date", date_from.isoformat()),
                LessThanOrEqual("date", date_to.isoformat()),
            )

            # Scan table with filter
            scan = table.scan(row_filter=filter_expr)
            arrow_table: pa.Table = scan.to_arrow()

            # Convert to list of dicts
            return arrow_table.to_pylist()

        except Exception as e:
            logger.error(
                "iceberg_query_failed", table="gold.dc_daily_kpis", error=str(e)
            )
            raise

    async def get_inventory_accuracy_trend(
        self, facility_id: str, days: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch inventory accuracy trend from gold.dc_daily_kpis."""
        from datetime import timedelta

        try:
            catalog = self._get_catalog()
            table = catalog.load_table("gold.dc_daily_kpis")

            date_to = date.today()
            date_from = date_to - timedelta(days=days)

            filter_expr = And(
                EqualTo("facility_id", facility_id),
                GreaterThanOrEqual("date", date_from.isoformat()),
                LessThanOrEqual("date", date_to.isoformat()),
            )

            scan = table.scan(
                row_filter=filter_expr,
                selected_fields=["date", "inventory_accuracy_pct", "cycle_counts"],
            )
            arrow_table: pa.Table = scan.to_arrow()

            return arrow_table.to_pylist()

        except Exception as e:
            logger.error(
                "iceberg_query_failed", table="gold.dc_daily_kpis", error=str(e)
            )
            raise


# Global client instance
_iceberg_client: IcebergClient | None = None


def init_iceberg_client(settings: Settings) -> IcebergClient:
    """Initialize global Iceberg client."""
    global _iceberg_client
    _iceberg_client = IcebergClient(settings)
    return _iceberg_client


def get_iceberg_client() -> IcebergClient:
    """Get Iceberg client instance."""
    if _iceberg_client is None:
        raise RuntimeError("Iceberg client not initialized")
    return _iceberg_client
