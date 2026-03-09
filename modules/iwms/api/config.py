"""iWMS API Configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service identification
    SERVICE_NAME: str = "iwms-api"
    SERVICE_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://logisense:logisense_dev@localhost:5432/logisense"  # pragma: allowlist secret

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CLIENT_ID: str = "iwms-api"

    # Vault
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: str = "dev-root-token"  # pragma: allowlist secret

    # Keycloak
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "logisense"
    KEYCLOAK_VERIFY_SSL: bool = False

    # API Settings
    API_PREFIX: str = "/v1/iwms"
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200

    @property
    def jwks_url(self) -> str:
        """Get JWKS URL for token validation."""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    @property
    def issuer_url(self) -> str:
        """Get issuer URL for token validation."""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
