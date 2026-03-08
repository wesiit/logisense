"""License management endpoints."""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import License, get_db_session
from app.schemas import (
    LicenseDetailResponse,
    LicenseIssueRequest,
    LicenseIssueResponse,
    LicenseValidateRequest,
    LicenseValidateResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/license", tags=["licenses"])

# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
MasterKeyHeader = Annotated[str | None, Header(alias="X-Master-Key")]


def verify_master_key(
    x_master_key: MasterKeyHeader = None,
    settings: AppSettings = None,  # type: ignore[assignment]
) -> None:
    """Verify the master API key for protected endpoints."""
    if not x_master_key or x_master_key != settings.master_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing master API key",
        )


def create_license_token(
    license_data: License,
    settings: Settings,
) -> str:
    """Create a signed JWT license token."""
    now = datetime.now(UTC)
    payload = {
        "sub": license_data.tenant_id,
        "tenant_id": license_data.tenant_id,
        "tenant_name": license_data.tenant_name,
        "licensed_modules": license_data.licensed_modules,
        "facility_count": license_data.facility_count,
        "tier": license_data.tier,
        "iat": int(now.timestamp()),
        "exp": int(license_data.expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_license_token(
    token: str,
    settings: Settings,
) -> dict | None:
    """Decode and verify a license token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Create a hash of the token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post(
    "/issue",
    response_model=LicenseIssueResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_master_key)],
)
async def issue_license(
    request: LicenseIssueRequest,
    db: DbSession,
    settings: AppSettings,
) -> LicenseIssueResponse:
    """
    Issue a new license for a tenant.

    Requires X-Master-Key header with valid master API key.
    """
    log = logger.bind(tenant_id=request.tenant_id)
    log.info("Issuing license")

    # Check if license already exists for tenant
    existing = await db.execute(select(License).where(License.tenant_id == request.tenant_id))
    existing_license = existing.scalar_one_or_none()

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=request.valid_days)

    if existing_license:
        # Update existing license
        existing_license.tenant_name = request.tenant_name
        existing_license.licensed_modules = request.licensed_modules
        existing_license.facility_count = request.facility_count
        existing_license.tier = request.tier
        existing_license.issued_at = now
        existing_license.expires_at = expires_at
        existing_license.is_active = True
        license_record = existing_license
        log.info("Updated existing license")
    else:
        # Create new license
        license_record = License(
            tenant_id=request.tenant_id,
            tenant_name=request.tenant_name,
            licensed_modules=request.licensed_modules,
            facility_count=request.facility_count,
            tier=request.tier,
            issued_at=now,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(license_record)
        log.info("Created new license")

    # Generate JWT token
    token = create_license_token(license_record, settings)

    # Store token hash for revocation checking
    license_record.token_hash = hash_token(token)

    await db.flush()

    return LicenseIssueResponse(
        license_token=token,
        expires_at=expires_at,
        licensed_modules=request.licensed_modules,
    )


@router.post("/validate", response_model=LicenseValidateResponse)
async def validate_license(
    request: LicenseValidateRequest,
    db: DbSession,
    settings: AppSettings,
) -> LicenseValidateResponse:
    """
    Validate a license token and check if a module is licensed.

    Returns valid=false if:
    - Token is invalid or expired
    - Module is not in the licensed modules list
    - License has been revoked (is_active=false)
    """
    log = logger.bind(module_id=request.module_id)

    # Decode token
    payload = decode_license_token(request.token, settings)
    if not payload:
        log.warning("Invalid license token")
        return LicenseValidateResponse(
            valid=False,
            message="Invalid or expired license token",
        )

    tenant_id = payload.get("tenant_id")
    licensed_modules = payload.get("licensed_modules", [])
    facility_count = payload.get("facility_count", 0)

    # Check if license is still active in database
    result = await db.execute(select(License).where(License.tenant_id == tenant_id))
    license_record = result.scalar_one_or_none()

    if not license_record:
        log.warning("License not found in database", tenant_id=tenant_id)
        return LicenseValidateResponse(
            valid=False,
            tenant_id=tenant_id,
            message="License not found",
        )

    if not license_record.is_active:
        log.warning("License is revoked", tenant_id=tenant_id)
        return LicenseValidateResponse(
            valid=False,
            tenant_id=tenant_id,
            message="License has been revoked",
        )

    # Check token hash matches (to detect if a new token was issued)
    token_hash = hash_token(request.token)
    if license_record.token_hash and license_record.token_hash != token_hash:
        log.warning("Token hash mismatch - using old token", tenant_id=tenant_id)
        return LicenseValidateResponse(
            valid=False,
            tenant_id=tenant_id,
            message="License token has been superseded",
        )

    # Check if module is licensed
    if request.module_id not in licensed_modules:
        log.info(
            "Module not licensed",
            tenant_id=tenant_id,
            requested_module=request.module_id,
            licensed_modules=licensed_modules,
        )
        return LicenseValidateResponse(
            valid=False,
            tenant_id=tenant_id,
            licensed_modules=licensed_modules,
            facility_count=facility_count,
            message=f"Module '{request.module_id}' is not licensed",
        )

    log.info("License validated successfully", tenant_id=tenant_id)
    return LicenseValidateResponse(
        valid=True,
        tenant_id=tenant_id,
        licensed_modules=licensed_modules,
        facility_count=facility_count,
    )


@router.get("/{tenant_id}", response_model=LicenseDetailResponse)
async def get_license(
    tenant_id: str,
    db: DbSession,
) -> LicenseDetailResponse:
    """Get current license details for a tenant."""
    result = await db.execute(select(License).where(License.tenant_id == tenant_id))
    license_record = result.scalar_one_or_none()

    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License not found for tenant: {tenant_id}",
        )

    return LicenseDetailResponse.model_validate(license_record)
