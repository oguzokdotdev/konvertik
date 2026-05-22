from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings


engine: AsyncEngine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.sqlite_db_path}",
    echo=settings.debug,
)


async def init_db() -> None:
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSession(engine) as session:
        yield session