"""JWT authentication for iWMS API."""

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import Settings, get_settings

logger = structlog.get_logger()

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)

# JWKS cache
_jwks_cache: dict | None = None


class TokenPayload(BaseModel):
    """Parsed JWT token payload."""

    sub: str  # Subject (user ID)
    email: str | None = None
    preferred_username: str | None = None
    name: str | None = None
    facility_id: str | None = None  # Custom claim for facility access
    roles: list[str] = []
    realm_access: dict | None = None


async def get_jwks(settings: Settings) -> dict:
    """Fetch JWKS from Keycloak."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    try:
        async with httpx.AsyncClient(verify=settings.KEYCLOAK_VERIFY_SSL) as client:
            response = await client.get(settings.jwks_url, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            return _jwks_cache
    except Exception as e:
        logger.error("jwks_fetch_failed", error=str(e), url=settings.jwks_url)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from None


def extract_roles(payload: dict) -> list[str]:
    """Extract roles from token payload."""
    roles: list[str] = []

    # Realm roles
    realm_access = payload.get("realm_access", {})
    roles.extend(realm_access.get("roles", []))

    # Resource roles
    resource_access = payload.get("resource_access", {})
    for resource, access in resource_access.items():
        for role in access.get("roles", []):
            roles.append(f"{resource}:{role}")

    return roles


async def validate_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> TokenPayload:
    """Validate JWT token and return payload."""
    # Test mode bypass - return mock token payload
    if settings.TEST_MODE:
        return TokenPayload(
            sub="test-user-id",
            email="test@logisense.io",
            preferred_username="test-user",
            name="Test User",
            facility_id=None,  # Allow access to all facilities in test mode
            roles=["admin", "warehouse-manager"],
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Get JWKS
        jwks = await get_jwks(settings)

        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Find matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience="account",  # Keycloak default audience
            issuer=settings.issuer_url,
            options={
                "verify_aud": False,  # Keycloak doesn't always set audience
                "verify_iss": True,
            },
        )

        # Extract roles
        roles = extract_roles(payload)

        # Extract facility_id from custom claim or groups
        facility_id = payload.get("facility_id")
        if not facility_id:
            # Try to extract from groups
            groups = payload.get("groups", [])
            for group in groups:
                if group.startswith("/facilities/"):
                    facility_id = group.split("/")[-1]
                    break

        return TokenPayload(
            sub=payload.get("sub", ""),
            email=payload.get("email"),
            preferred_username=payload.get("preferred_username"),
            name=payload.get("name"),
            facility_id=facility_id,
            roles=roles,
        )

    except JWTError as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


async def get_optional_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> TokenPayload | None:
    """Optionally validate JWT token (for endpoints that work with or without auth)."""
    if not credentials:
        return None
    return await validate_token(credentials, settings)


def require_role(required_role: str):
    """Dependency to require a specific role."""

    async def _check_role(
        token: TokenPayload = Depends(validate_token),
    ) -> TokenPayload:
        if required_role not in token.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}",
            )
        return token

    return _check_role


def require_facility_access(facility_id_param: str = "facility_id"):
    """Dependency to validate facility access."""

    async def _check_facility(
        token: TokenPayload = Depends(validate_token),
        facility_id: str | None = None,
    ) -> str:
        # If user has a specific facility in token, validate it matches
        if token.facility_id and facility_id and token.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this facility",
            )

        # Return the facility_id (from token if not provided)
        return facility_id or token.facility_id or ""

    return _check_facility
