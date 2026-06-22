from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from app.infrastructure.db.models import Base


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:  # type: ignore[no-untyped-def]
    url = postgres_container.get_connection_url()
    return url.replace("psycopg2", "asyncpg").replace(
        "postgresql://", "postgresql+asyncpg://"
    )


@pytest_asyncio.fixture(scope="session")
async def db_engine(db_url: str):  # type: ignore[no-untyped-def]
    engine = create_async_engine(db_url, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def session(db_engine) -> AsyncIterator[AsyncSession]:  # type: ignore[no-untyped-def]
    conn = await db_engine.connect()
    await conn.begin()

    s = AsyncSession(
        bind=conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield s
    finally:
        await s.close()
        await conn.rollback()
        await conn.close()
