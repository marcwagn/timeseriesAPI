import asyncpg
import pytest
from contextlib import asynccontextmanager
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from sqlalchemy import text

from src.core.config import Config
from src.db.schema import Base

import src.db.init_models  # noqa: F401 - registers models with Base


test_config = Config(_env_file=Path(__file__).parent.parent / "src" / ".env.test")

test_engine = create_async_engine(test_config.db_timescale_url)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def _ensure_database_exists():
    """Create the test database if it does not already exist."""
    conn = await asyncpg.connect(
        user=test_config.timescale_user,
        password=test_config.timescale_password,
        host=test_config.db_host,
        port=test_config.db_port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", test_config.db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{test_config.db_name}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Create the test database if needed, then drop and recreate all tables."""
    await _ensure_database_exists()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
async def clean_database(setup_database):
    """Truncate all tables before and after each test to ensure isolation."""
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE timeseries_data, timeseries, users CASCADE"))
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE timeseries_data, timeseries, users CASCADE"))


@pytest.fixture
async def db_session():
    """Provide a test database session, rolled back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client():
    """Base HTTP test client with the app lifespan replaced with a no-op."""
    from src.main import app

    @asynccontextmanager
    async def test_lifespan(app):
        yield  # no-op: setup_database fixture manages table creation

    app.router.lifespan_context = test_lifespan

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
