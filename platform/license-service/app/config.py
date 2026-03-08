"""License Service configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://logisense:logisense_dev@localhost:5432/logisense"  # pragma: allowlist secret

    # JWT Configuration
    jwt_secret_key: str = "logisense-license-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    # API Security
    master_api_key: str = "logisense-master-api-key-change-in-production"

    # Service Info
    service_name: str = "license-service"
    service_version: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
