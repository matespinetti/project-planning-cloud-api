"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    DATABASE_URL: str

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "ProjectPlanning Cloud Persistence API"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Security & JWT
    JWT_SECRET_KEY: str = "change-me-access-secret"
    JWT_REFRESH_SECRET_KEY: str = "change-me-refresh-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Integrations
    BONITA_API_KEY: str | None = None
    BONITA_SYSTEM_USER_ID: str | None = None

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Create and cache a singleton Settings instance."""
    return Settings()
