import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings
from src.core.db import get_session
from src.models.task import ConversionTask
from src.storage.local import delete_file


def expires_at_for_plan(plan_tier: str, now: datetime | None = None) -> datetime:
    """Return file expiration datetime for a plan tier."""
    base = now or datetime.now(timezone.utc)
    minutes = (
        settings.pro_file_ttl_minutes
        if plan_tier == "pro"
        else settings.free_file_ttl_minutes
    )
    return base + timedelta(minutes=minutes)


async def mark_stale_tasks_failed() -> None:
    """Recover tasks left in progress across restarts."""
    async for session in get_session():
        statement = select(ConversionTask).where(
            ConversionTask.status.in_(("pending", "in_progress"))
        )
        results = await session.exec(statement)
        tasks = results.all()

        if not tasks:
            return

        now = datetime.now(timezone.utc)
        for task in tasks:
            task.status = "failed"
            if not task.error_message:
                task.error_message = "Task interrupted by application restart."
            task.updated_at = now
            session.add(task)

        await session.commit()
        return


async def cleanup_expired_tasks() -> None:
    """Delete expired input/output files and update task state."""
    async for session in get_session():
        await _cleanup_expired_tasks(session)
        return


async def _cleanup_expired_tasks(session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    statement = select(ConversionTask).where(
        ConversionTask.expires_at.is_not(None),
        ConversionTask.expires_at <= now,
    )
    results = await session.exec(statement)
    tasks = results.all()

    for task in tasks:
        await _expire_task_files(task)
        if task.status == "completed":
            task.status = "expired"
        elif task.status in {"pending", "in_progress"}:
            task.status = "failed"
            if not task.error_message:
                task.error_message = "Task expired before completion."
        task.updated_at = now
        session.add(task)

    if tasks:
        await session.commit()


async def _expire_task_files(task: ConversionTask) -> None:
    if task.input_path:
        await delete_file(Path(task.input_path))
        task.input_path = None

    if task.output_path:
        await delete_file(Path(task.output_path))
        task.output_path = None


async def cleanup_loop(stop_event: asyncio.Event) -> None:
    """Run periodic retention cleanup inside the app process."""
    while not stop_event.is_set():
        await cleanup_expired_tasks()
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.cleanup_interval_seconds,
            )
        except asyncio.TimeoutError:
            continue
