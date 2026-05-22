from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from taskiq.brokers.inmemory_broker import InMemoryBroker

from src.core.db import get_session
from src.models.task import ConversionTask
from src.services.converter import ConversionError, convert
from src.storage.local import delete_file, get_output_path

broker = InMemoryBroker()


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

        input_path = Path(task.input_path)
        output_path = get_output_path(input_path, task.target_format)

        try:
            await convert(input_path, output_path)

            task.status = "completed"
            task.output_path = str(output_path)

        except ConversionError as e:
            task.status = "failed"
            task.error_message = str(e)

        finally:
            task.updated_at = datetime.now(timezone.utc)
            session.add(task)
            await session.commit()

            if task.status == "completed":
                await delete_file(input_path)