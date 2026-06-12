"""arq worker entrypoint. Ingestion jobs will be registered here in the next phase."""

from arq.connections import RedisSettings

from app.config import get_settings


async def ping(ctx: dict) -> str:
    """Smoke job to verify the worker picks up tasks from Redis."""
    return "pong"


class WorkerSettings:
    functions = [ping]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
