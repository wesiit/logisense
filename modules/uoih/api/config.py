"""Configuration settings for UOIH API."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service info
    SERVICE_NAME: str = "uoih-api"
    SERVICE_VERSION: str = "0.1.0"
    API_PREFIX: str = "/v1/uoih"
    DEBUG: bool = False
    TEST_MODE: bool = False

    # Database
    DATABASE_URL: str = (  # pragma: allowlist secret
        "postgresql+asyncpg://logisense:logisense_dev@localhost:5432/logisense"
    )

    # Iceberg / MinIO
    ICEBERG_CATALOG_URI: str = "http://localhost:8181"
    ICEBERG_WAREHOUSE: str = "s3://logisense-gold/"
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"

    # Observability
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
