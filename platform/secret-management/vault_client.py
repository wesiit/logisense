"""
LogiSense Vault Client
======================

A Python helper for interacting with HashiCorp Vault to retrieve secrets
and database credentials.

Usage:
    from vault_client import get_secret, get_db_credentials

    # Get static secrets
    kafka_config = get_secret("logisense/dev/kafka")
    print(kafka_config["bootstrap_servers"])

    # Get dynamic database credentials
    username, password = get_db_credentials()

Environment Variables:
    VAULT_ADDR: Vault server address (default: http://localhost:8200)
    VAULT_TOKEN: Vault token for authentication
    VAULT_ROLE_ID: AppRole Role ID (alternative to token)
    VAULT_SECRET_ID: AppRole Secret ID (alternative to token)
"""

import os
import time
from functools import lru_cache
from http import HTTPStatus
from typing import Any

import requests


class VaultError(Exception):
    """Base exception for Vault errors."""


class VaultAuthError(VaultError):
    """Authentication error."""


class VaultSecretNotFoundError(VaultError):
    """Secret not found."""


class VaultClient:
    """Client for interacting with HashiCorp Vault."""

    def __init__(
        self,
        addr: str | None = None,
        token: str | None = None,
        role_id: str | None = None,
        secret_id: str | None = None,
    ) -> None:
        """
        Initialize Vault client.

        Args:
            addr: Vault server address
            token: Vault token (if using token auth)
            role_id: AppRole Role ID (if using AppRole auth)
            secret_id: AppRole Secret ID (if using AppRole auth)
        """
        self.addr = addr or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self._token = token or os.getenv("VAULT_TOKEN")
        self._role_id = role_id or os.getenv("VAULT_ROLE_ID")
        self._secret_id = secret_id or os.getenv("VAULT_SECRET_ID")
        self._token_expiry: float = 0

        # If no token but AppRole credentials provided, authenticate
        if not self._token and self._role_id and self._secret_id:
            self._authenticate_approle()

    def _authenticate_approle(self) -> None:
        """Authenticate using AppRole and get a token."""
        url = f"{self.addr}/v1/auth/approle/login"
        payload = {
            "role_id": self._role_id,
            "secret_id": self._secret_id,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()

            self._token = data["auth"]["client_token"]
            lease_duration = data["auth"]["lease_duration"]
            self._token_expiry = (
                time.time() + lease_duration - 60
            )  # Refresh 1 min early

        except requests.RequestException as e:
            raise VaultAuthError(f"AppRole authentication failed: {e}") from e

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid token, refreshing if needed."""
        token_expired = self._token_expiry and time.time() >= self._token_expiry
        has_approle_creds = self._role_id and self._secret_id
        if token_expired and has_approle_creds:
            self._authenticate_approle()

        if not self._token:
            raise VaultAuthError(
                "No Vault token available. Set VAULT_TOKEN or provide AppRole credentials."
            )

    @property
    def _headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        self._ensure_authenticated()
        # At this point _token is guaranteed non-None by _ensure_authenticated
        assert self._token is not None
        return {"X-Vault-Token": self._token}

    def get_secret(self, path: str) -> dict[str, Any]:
        """
        Get a secret from Vault KV v2 secrets engine.

        Args:
            path: Secret path (e.g., "logisense/dev/kafka")

        Returns:
            Dictionary containing the secret data

        Raises:
            VaultSecretNotFoundError: If secret doesn't exist
            VaultError: For other Vault errors
        """
        # For KV v2, we need to add /data/ to the path
        if not path.startswith("logisense/data/"):
            parts = path.split("/", 1)
            mount_and_subpath = 2
            if len(parts) == mount_and_subpath:
                path = f"{parts[0]}/data/{parts[1]}"

        url = f"{self.addr}/v1/{path}"

        try:
            response = requests.get(url, headers=self._headers, timeout=10)

            if response.status_code == HTTPStatus.NOT_FOUND:
                raise VaultSecretNotFoundError(f"Secret not found: {path}")

            response.raise_for_status()
            data: dict[str, Any] = response.json()
            inner: dict[str, Any] = data.get("data", {})
            return dict(inner.get("data", {}))

        except requests.RequestException as e:
            if isinstance(e, VaultSecretNotFoundError):
                raise
            raise VaultError(f"Failed to get secret: {e}") from e

    def get_database_credentials(self, role: str = "logisense-app") -> tuple[str, str]:
        """
        Get dynamic database credentials from Vault.

        Args:
            role: Database role name

        Returns:
            Tuple of (username, password)

        Raises:
            VaultError: If unable to get credentials
        """
        url = f"{self.addr}/v1/database/creds/{role}"

        try:
            response = requests.get(url, headers=self._headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            username = data["data"]["username"]
            password = data["data"]["password"]

            return username, password

        except requests.RequestException as e:
            raise VaultError(f"Failed to get database credentials: {e}") from e

    def is_healthy(self) -> bool:
        """Check if Vault is healthy and accessible."""
        try:
            response = requests.get(f"{self.addr}/v1/sys/health", timeout=5)
            return response.status_code in (200, 429, 472, 473)
        except requests.RequestException:
            return False


# Module-level client instance (lazy initialization)
_client: VaultClient | None = None


def _get_client() -> VaultClient:
    """Get or create the module-level Vault client."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = VaultClient()
    return _client


# Cache TTL tracking for credentials
_credentials_cache: dict[str, tuple[tuple[str, str], float]] = {}
CREDENTIALS_CACHE_TTL = 300  # 5 minutes


def get_secret(path: str) -> dict[str, Any]:
    """
    Get a secret from Vault.

    This is a convenience function using the module-level client.

    Args:
        path: Secret path (e.g., "logisense/dev/kafka")

    Returns:
        Dictionary containing the secret data
    """
    return _get_client().get_secret(path)


def get_db_credentials(role: str = "logisense-app") -> tuple[str, str]:
    """
    Get dynamic database credentials from Vault with caching.

    Credentials are cached for 5 minutes to reduce Vault API calls.
    Each call generates new credentials if cache is expired.

    Args:
        role: Database role name

    Returns:
        Tuple of (username, password)
    """
    cache_key = role
    now = time.time()

    # Check cache
    if cache_key in _credentials_cache:
        cached_creds, expiry = _credentials_cache[cache_key]
        if now < expiry:
            return cached_creds

    # Get fresh credentials
    credentials = _get_client().get_database_credentials(role)

    # Cache with 5-minute TTL
    _credentials_cache[cache_key] = (credentials, now + CREDENTIALS_CACHE_TTL)

    return credentials


def clear_credentials_cache() -> None:
    """Clear the credentials cache, forcing fresh credentials on next call."""
    _credentials_cache.clear()


# Cached secret getter using lru_cache
@lru_cache(maxsize=32)
def get_secret_cached(path: str) -> tuple[tuple[str, str], ...]:
    """
    Get a secret from Vault with LRU caching.

    Note: This caches indefinitely until cache is cleared or maxsize is reached.
    Use get_secret() for non-cached access.

    Args:
        path: Secret path

    Returns:
        Secret data as tuple of key-value tuples (for hashability)
    """
    secret = get_secret(path)
    return tuple(secret.items())


def get_secret_cached_as_dict(path: str) -> dict[str, Any]:
    """
    Get a cached secret as a dictionary.

    Args:
        path: Secret path

    Returns:
        Dictionary containing the secret data
    """
    return dict(get_secret_cached(path))


if __name__ == "__main__":
    # Self-test
    print("LogiSense Vault Client - Self Test")
    print("=" * 40)

    client = VaultClient()

    print(f"Vault Address: {client.addr}")
    print(f"Vault Healthy: {client.is_healthy()}")

    if client.is_healthy():
        print("\nTesting secret retrieval...")
        try:
            kafka = get_secret("logisense/dev/kafka")
            print(f"  Kafka config: {kafka}")
        except VaultError as e:
            print(f"  Error: {e}")

        print("\nTesting database credentials...")
        try:
            username, password = get_db_credentials()
            print(f"  Username: {username}")
            print(f"  Password: {'*' * len(password)}")
        except VaultError as e:
            print(f"  Error: {e}")
