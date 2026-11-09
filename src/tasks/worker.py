
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from taskiq.brokers.inmemory_broker import InMemoryBroker

from src.core.config import settings
from src.core.db import get_session
from src.models.task import ConversionTask
from src.services.converter import ConversionError, convert
from src.services.retention import expires_at_for_plan
from src.storage.local import get_output_path

broker = InMemoryBroker()
conversion_slots = asyncio.Semaphore(settings.max_parallel_conversions)


@broker.task
async def convert_file_task(task_id: str) -> None:
    """Pick up a conversion task and run ffmpeg."""
    async for session in get_session():
        task = await session.get(ConversionTask, UUID(task_id))

        if task is None:
            return

        # Активная задача не должна иметь срока удаления.
        task.status = "in_progress"
        task.expires_at = None
        task.updated_at = datetime.now(timezone.utc)

        session.add(task)
        await session.commit()

        if task.input_path is None:
            finished_at = datetime.now(timezone.utc)

            task.status = "failed"
            task.error_message = "Input file path is missing."
            task.expires_at = expires_at_for_plan(
                task.plan_tier,
                now=finished_at,
            )
            task.updated_at = finished_at

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

        except Exception as e:
            task.status = "failed"
            task.error_message = f"Unexpected conversion error: {e}"

        finally:
            # TTL начинается только после окончания обработки.
            finished_at = datetime.now(timezone.utc)

            task.expires_at = expires_at_for_plan(
                task.plan_tier,
                now=finished_at,
            )
            task.updated_at = finished_at

            session.add(task)
            await session.commit()
