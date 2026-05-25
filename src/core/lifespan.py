import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from src.core.db import init_db
from src.services.retention import cleanup_expired_tasks, cleanup_loop, mark_stale_tasks_failed


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize resources on startup."""
    await init_db()
    await mark_stale_tasks_failed()
    await cleanup_expired_tasks()

    stop_event = asyncio.Event()
    cleanup_task = asyncio.create_task(cleanup_loop(stop_event))

    try:
        yield
    finally:
        stop_event.set()
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
