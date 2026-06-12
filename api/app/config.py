from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# dev fallback only; startup refuses to run with this value outside ENVIRONMENT=dev.
# Kept >= 32 bytes to satisfy the HS256 key length requirement (RFC 7518 3.2)
DEV_JWT_SECRET = "dev-only-secret-not-for-production-use-0000"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "dev"

    # 5433 matches the compose port mapping for the db service
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/documind"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    # window in which a replayed (just rotated) refresh token is treated as a
    # benign client race instead of theft
    refresh_reuse_grace_seconds: int = 10

    # secure=False so the cookie works over plain http in local dev
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
