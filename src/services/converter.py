import asyncio
from pathlib import Path


class ConversionError(Exception):
    """Raised when ffmpeg conversion fails."""


async def convert(input_path: Path, output_path: Path) -> None:
    """Convert a file using ffmpeg.

    Args:
        input_path: Path to the source file.
        output_path: Path for the converted output file.

    Raises:
        ConversionError: If ffmpeg exits with a non-zero code.
    """
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", str(input_path),
        "-y",
        str(output_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    if process.returncode != 0:
        error = stderr.decode(errors="replace").strip()
        raise ConversionError(f"ffmpeg failed: {error}")