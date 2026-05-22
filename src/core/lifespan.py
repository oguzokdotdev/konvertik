from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from src.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize resources on startup."""
    await init_db()
    yield