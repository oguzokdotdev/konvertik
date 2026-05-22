from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
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
    file: UploadFile,
    target_format: str,
    plan_tier: str = "free",
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Accept a file upload and enqueue a conversion task."""
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


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Get conversion task status by ID."""
    task = await session.get(ConversionTask, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return TaskResponse.model_validate(task)