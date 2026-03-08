"""Pydantic v2 schemas for License Service."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Request Schemas
# ============================================================================


class LicenseIssueRequest(BaseModel):
    """Request body for issuing a new license."""

    tenant_id: str = Field(..., min_length=1, max_length=64)
    tenant_name: str = Field(..., min_length=1, max_length=255)
    licensed_modules: list[str] = Field(
        ...,
        min_length=1,
        description="List of module IDs (iwms, lip, ccvp, pise, wcvp, uoih)",
    )
    facility_count: int = Field(default=1, ge=1)
    tier: str = Field(default="standard", pattern="^(starter|standard|enterprise)$")
    valid_days: int = Field(default=365, ge=1, le=3650)


class LicenseValidateRequest(BaseModel):
    """Request body for validating a license token."""

    token: str = Field(..., min_length=1)
    module_id: str = Field(..., min_length=1)


# ============================================================================
# Response Schemas
# ============================================================================


class LicenseIssueResponse(BaseModel):
    """Response for license issuance."""

    license_token: str
    expires_at: datetime
    licensed_modules: list[str]


class LicenseValidateResponse(BaseModel):
    """Response for license validation."""

    valid: bool
    tenant_id: str | None = None
    licensed_modules: list[str] = Field(default_factory=list)
    facility_count: int = 0
    message: str | None = None


class LicenseDetailResponse(BaseModel):
    """Response for license details."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    tenant_name: str
    licensed_modules: list[str]
    facility_count: int
    tier: str
    issued_at: datetime
    expires_at: datetime
    is_active: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    service: str = "license-service"


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: str | None = None
