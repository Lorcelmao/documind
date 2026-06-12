import asyncio
import os

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import create_app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/documind_test",
)


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_database() -> None:
    """Create the test database if missing. Sync fixture so it owns its own event loop."""

    url = make_url(TEST_DATABASE_URL)
    admin_dsn = url.set(database="postgres").render_as_string(hide_password=False)
    admin_dsn = admin_dsn.replace("postgresql+asyncpg://", "postgresql://")

    async def ensure() -> None:
        conn = await asyncpg.connect(admin_dsn)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", url.database
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{url.database}"')
        finally:
            await conn.close()

    asyncio.run(ensure())


@pytest.fixture
async def db_engine():
    """Fresh schema per test. NullPool avoids connection reuse across event loops."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_and_login(
    client: AsyncClient, email: str = "user@example.com", password: str = "password123"
) -> dict[str, str]:
    """Helper: returns Authorization headers for a fresh user. Refresh cookie lands in the jar."""
    res = await client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    res = await client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
