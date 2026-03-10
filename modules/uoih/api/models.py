"""SQLAlchemy models for UOIH schema."""

import os
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Support SQLite for testing (no schema support)
TEST_MODE = os.environ.get("TEST_MODE") == "true"
SCHEMA = None if TEST_MODE else "uoih"


def pk_uuid() -> dict:
    """Generate primary key UUID kwargs compatible with SQLite and PostgreSQL."""
    kwargs: dict = {"primary_key": True, "default": uuid4}
    if not TEST_MODE:
        kwargs["server_default"] = func.gen_random_uuid()
    return kwargs


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Alert(Base):
    """Operational alerts for facilities."""

    __tablename__ = "alerts"
    __table_args__ = {"schema": SCHEMA} if SCHEMA else {}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), **pk_uuid())
    facility_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(50), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # CRITICAL/HIGH/MEDIUM/LOW
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE"
    )  # ACTIVE/ACKNOWLEDGED/RESOLVED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
