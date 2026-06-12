from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.config import DEV_JWT_SECRET, get_settings
from app.database import engine
from app.workspaces.router import router as workspaces_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.environment != "dev" and settings.jwt_secret == DEV_JWT_SECRET:
        raise RuntimeError("JWT_SECRET is still the dev fallback; set a real secret")
    app.state.redis = aioredis.from_url(settings.redis_url)
    yield
    await app.state.redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="DocuMind API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(workspaces_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await app.state.redis.ping()
        return {"status": "ok"}

    return app


app = create_app()
