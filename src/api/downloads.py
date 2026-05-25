from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.db import get_session
from src.models.task import ConversionTask

router = APIRouter(prefix="/download", tags=["downloads"])


@router.get("/{task_id}")
async def download_file(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Download a converted file by task ID."""
    task = await session.get(ConversionTask, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not completed yet. Current status: {task.status}",
        )

    if task.output_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file not found or already expired.",
        )

    output_path = Path(task.output_path)

    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file has been deleted or expired.",
        )

    download_name = (
        f"{Path(task.file_name).stem}.{task.target_format}"
    )

    return FileResponse(
        path=output_path,
        filename=download_name,
        media_type="application/octet-stream",
    )
