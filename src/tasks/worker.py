import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from taskiq.brokers.inmemory_broker import InMemoryBroker

from src.core.config import settings
from src.core.db import get_session
from src.models.task import ConversionTask
from src.services.converter import ConversionError, convert
from src.storage.local import get_output_path

broker = InMemoryBroker()
conversion_slots = asyncio.Semaphore(settings.max_parallel_conversions)


@broker.task
async def convert_file_task(task_id: str) -> None:
    """Pick up a conversion task and run ffmpeg.

    Args:
        task_id: UUID string of the ConversionTask to process.
    """
    async for session in get_session():
        task = await session.get(ConversionTask, UUID(task_id))

        if task is None:
            return

        task.status = "in_progress"
        task.updated_at = datetime.now(timezone.utc)
        session.add(task)
        await session.commit()

        if task.input_path is None:
            task.status = "failed"
            task.error_message = "Input file path is missing."
            task.updated_at = datetime.now(timezone.utc)
            session.add(task)
            await session.commit()
            return

        input_path = Path(task.input_path)
        output_path = get_output_path(input_path, task.target_format)

        try:
            async with conversion_slots:
                await convert(
                    input_path,
                    output_path,
                    task.target_format,
                    task.plan_tier,
                )

            task.status = "completed"
            task.output_path = str(output_path)
            task.completed_at = datetime.now(timezone.utc)

        except ConversionError as e:
            task.status = "failed"
            task.error_message = str(e)

        finally:
            task.updated_at = datetime.now(timezone.utc)
            session.add(task)
            await session.commit()
