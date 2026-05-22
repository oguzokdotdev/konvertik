import uuid
from pathlib import Path

import aiofiles

from src.core.config import settings


def _uploads_dir() -> Path:
    """Return uploads directory, creating it if needed."""
    path = Path(settings.uploads_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_input_path(filename: str) -> Path:
    """Generate a unique path for an uploaded file."""
    suffix = Path(filename).suffix
    unique_name = f"{uuid.uuid4()}{suffix}"
    return _uploads_dir() / unique_name


def get_output_path(input_path: Path, target_format: str) -> Path:
    """Generate output path based on input path and target format."""
    return input_path.with_suffix(f".out.{target_format}")


async def save_upload(data: bytes, filename: str) -> Path:
    """Save uploaded file bytes to disk and return the path."""
    path = get_input_path(filename)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)
    return path


async def delete_file(path: Path) -> None:
    """Delete a file from disk if it exists."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass