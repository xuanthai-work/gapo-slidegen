import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"timeout": 8},
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.SQL_ECHO,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
DB_CONNECT_ATTEMPTS = 3


async def open_db_session() -> AsyncSession:
    for attempt in range(DB_CONNECT_ATTEMPTS):
        session = SessionFactory()
        try:
            # Establish the connection here so a transient Neon wake-up/TLS
            # reset can be retried before endpoint code starts a transaction.
            await session.connection()
        except (OSError, DBAPIError):
            await session.close()
            if attempt == DB_CONNECT_ATTEMPTS - 1:
                raise
            await engine.dispose()
            await asyncio.sleep(0.25 * (attempt + 1))
        else:
            return session

    raise RuntimeError("Database retry loop ended unexpectedly")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session = await open_db_session()
    try:
        yield session
    finally:
        await session.close()
