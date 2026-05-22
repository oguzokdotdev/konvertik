from uuid import UUID

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings
from src.models.task import ConversionTask


class QuotaExceeded(Exception):
    """Raised when a user exceeds their plan limits."""


async def check_file_size(file_size: int, plan_tier: str) -> None:
    """Raise QuotaExceeded if file exceeds plan limit."""
    limit_bytes = settings.free_max_file_size_mb * 1024 * 1024

    if plan_tier == "free" and file_size > limit_bytes:
        raise QuotaExceeded(
            f"File exceeds free plan limit of {settings.free_max_file_size_mb}MB."
        )


async def check_daily_conversions(
    session: AsyncSession,
    plan_tier: str,
) -> None:
    """Raise QuotaExceeded if daily conversion limit is reached."""
    if plan_tier != "free":
        return

    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date()

    statement = select(func.count(ConversionTask.id)).where(
        func.date(ConversionTask.created_at) == today,
        ConversionTask.plan_tier == "free",
    )
    result = await session.exec(statement)
    count = result.one()

    if count >= settings.free_max_daily_conversions:
        raise QuotaExceeded(
            f"Daily limit of {settings.free_max_daily_conversions} conversions reached."
        )