
import uuid
from pathlib import Path
from typing import Protocol

import aiofiles

from src.core.config import settings


CHUNK_SIZE = 5 * 1024 * 1024  # 5 MiB


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes:
        ...


class UploadTooLarge(Exception):
    """Raised when an uploaded file exceeds its size limit."""


class EmptyUpload(Exception):
    """Raised when an uploaded file is empty."""


def _uploads_dir() -> Path:
    """Return uploads directory, creating it if needed."""
    path = Path(settings.uploads_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_input_path(filename: str) -> Path:
    """Generate a unique path for an uploaded file."""
    suffix = Path(filename).suffix.lower()

    if (
        not suffix
        or len(suffix) > 16
        or not suffix[1:].isalnum()
    ):
        suffix = ""

    unique_name = f"{uuid.uuid4()}{suffix}"
    return _uploads_dir() / unique_name


def get_output_path(input_path: Path, target_format: str) -> Path:
    """Generate output path based on input path and target format."""
    return input_path.with_suffix(f".out.{target_format}")


async def save_upload(
    source: AsyncReadable,
    filename: str,
    max_size_bytes: int | None = None,
) -> tuple[Path, int]:
    """Stream an uploaded file to disk and return its path and size.

    The file is read in chunks to avoid loading the entire upload into RAM.
    If the size limit is exceeded or writing fails, the partial file is removed.
    """
    path = get_input_path(filename)
    total_size = 0

    try:
        async with aiofiles.open(path, "wb") as destination:
            while True:
                chunk = await source.read(CHUNK_SIZE)

                if not chunk:
                    break

                total_size += len(chunk)

                if (
                    max_size_bytes is not None
                    and total_size > max_size_bytes
                ):
                    raise UploadTooLarge

                await destination.write(chunk)

        if total_size == 0:
            raise EmptyUpload

        return path, total_size

    except BaseException:
        await delete_file(path)
        raise


async def delete_file(path: Path) -> None:
    """Delete a file from disk if it exists."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
