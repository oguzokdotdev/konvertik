from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import text
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings


engine: AsyncEngine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.sqlite_db_path}",
    echo=settings.debug,
)


async def init_db() -> None:
    """Create all tables on startup."""
    Path(settings.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await _upgrade_sqlite_schema(conn)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


async def _upgrade_sqlite_schema(conn) -> None:
    """Add new task columns to older SQLite databases."""
    result = await conn.execute(text("PRAGMA table_info(conversion_tasks)"))
    columns = {row[1] for row in result.fetchall()}

    upgrades = {
        "completed_at": (
            "ALTER TABLE conversion_tasks ADD COLUMN completed_at TIMESTAMP NULL"
        ),
        "expires_at": (
            "ALTER TABLE conversion_tasks ADD COLUMN expires_at TIMESTAMP NULL"
        ),
    }

    for column, statement in upgrades.items():
        if column not in columns:
            await conn.execute(text(statement))
