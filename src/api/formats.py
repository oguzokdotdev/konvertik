from fastapi import APIRouter

from src.services.formats import frontend_format_config

router = APIRouter(prefix="/formats", tags=["formats"])


@router.get("/")
async def get_formats() -> dict[str, object]:
    """Return supported conversion formats for the frontend."""
    return frontend_format_config()
