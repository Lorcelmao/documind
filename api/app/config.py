from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 5433 matches the compose port mapping for the db service
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/documind"
    redis_url: str = "redis://localhost:6379/0"

    # dev fallback only; must be overridden in any real deployment.
    # Kept >= 32 bytes to satisfy the HS256 key length requirement (RFC 7518 3.2)
    jwt_secret: str = "dev-only-secret-not-for-production-use-0000"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14

    # secure=False so the cookie works over plain http in local dev
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
