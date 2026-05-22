from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.db import get_session
from src.models.task import ConversionTask
from src.schemas.task import TaskResponse, UploadRequest
from src.services.quota import QuotaExceeded, check_daily_conversions, check_file_size
from src.storage.local import save_upload
from src.tasks.worker import convert_file_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "/upload",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile = File(...),
    target_format: str = Query(...),
    plan_tier: str = Query("free"),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Accept a file upload and enqueue a conversion task.

    Args:
        file: The uploaded media file.
        target_format: Desired output format (e.g. mp3, mp4).
        plan_tier: User plan — 'free' or 'pro'.
        session: Async database session.

    Raises:
        HTTPException 413: File exceeds plan size limit.
        HTTPException 429: Daily conversion limit reached.

    Returns:
        TaskResponse with the created task ID and initial status.
    """
    data = await file.read()
    file_size = len(data)

    try:
        await check_file_size(file_size, plan_tier)
        await check_daily_conversions(session, plan_tier)
    except QuotaExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )

    input_path = await save_upload(data, file.filename or "upload")

    task = ConversionTask(
        file_name=file.filename or "upload",
        file_size=file_size,
        target_format=target_format,
        plan_tier=plan_tier,
        input_path=str(input_path),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    await convert_file_task.kiq(str(task.id))

    return TaskResponse.model_validate(task)


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    limit: int = Query(12, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> List[TaskResponse]:
    """Return recent conversion tasks ordered by creation time.

    Args:
        limit: Maximum number of tasks to return (1–50).
        session: Async database session.

    Returns:
        List of TaskResponse ordered newest first.
    """
    statement = (
        select(ConversionTask)
        .order_by(ConversionTask.created_at.desc())
        .limit(limit)
    )
    results = await session.exec(statement)
    return [TaskResponse.model_validate(t) for t in results.all()]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Get conversion task status by ID.

    Args:
        task_id: UUID of the task.
        session: Async database session.

    Raises:
        HTTPException 404: Task not found.

    Returns:
        TaskResponse with current status.
    """
    task = await session.get(ConversionTask, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return TaskResponse.model_validate(task)