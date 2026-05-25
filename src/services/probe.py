import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from src.core.config import settings
from src.services.formats import MediaKind, kind_for_extension, normalize_format


class ProbeError(Exception):
    """Raised when ffprobe cannot inspect an uploaded file."""


IMAGE_FORMAT_NAMES = {
    "apng",
    "avif",
    "bmp_pipe",
    "dpx_pipe",
    "exr_pipe",
    "gif",
    "ico",
    "image2",
    "image2pipe",
    "jpeg_pipe",
    "jpegls_pipe",
    "png_pipe",
    "sgi_pipe",
    "tiff_pipe",
    "webp_pipe",
}


@dataclass(frozen=True)
class MediaInfo:
    """Media metadata needed to validate conversions."""

    kind: MediaKind
    source_format: str | None
    has_video: bool
    has_audio: bool
    has_subtitle: bool
    duration: float | None = None


async def probe_media(path: Path, original_name: str) -> MediaInfo:
    """Inspect a media file with ffprobe."""
    command = [
        settings.ffprobe_path,
        "-v", "error",
        "-show_entries", "format=format_name,duration:stream=codec_type",
        "-of", "json",
        str(path),
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as e:
        raise ProbeError(f"Cannot start ffprobe: {e}") from e

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=settings.ffprobe_timeout_seconds,
        )
    except asyncio.TimeoutError as e:
        process.kill()
        await process.wait()
        raise ProbeError("ffprobe timed out while reading the file.") from e

    if process.returncode != 0:
        message = stderr.decode(errors="replace").strip()
        raise ProbeError(message or "ffprobe could not read the file.")

    try:
        payload = json.loads(stdout.decode())
    except json.JSONDecodeError as e:
        raise ProbeError("ffprobe returned invalid metadata.") from e

    extension = normalize_format(Path(original_name).suffix)
    format_names = {
        normalize_format(name)
        for name in payload.get("format", {}).get("format_name", "").split(",")
        if name
    }
    streams = payload.get("streams", [])
    stream_types = {stream.get("codec_type") for stream in streams}

    has_video = "video" in stream_types
    has_audio = "audio" in stream_types
    has_subtitle = "subtitle" in stream_types
    source_format = _source_format(extension, format_names)
    kind = _media_kind(extension, format_names, has_video, has_audio, has_subtitle)
    duration = _duration(payload.get("format", {}).get("duration"))

    if kind is None:
        raise ProbeError("Unsupported or unknown media type.")

    return MediaInfo(
        kind=kind,
        source_format=source_format,
        has_video=has_video,
        has_audio=has_audio,
        has_subtitle=has_subtitle,
        duration=duration,
    )


def _source_format(extension: str, format_names: set[str]) -> str | None:
    """Pick the most user-facing source format."""
    if extension:
        return extension
    return next(iter(format_names), None)


def _media_kind(
    extension: str,
    format_names: set[str],
    has_video: bool,
    has_audio: bool,
    has_subtitle: bool,
) -> MediaKind | None:
    """Classify media by ffprobe output, falling back to extension."""
    extension_kind = kind_for_extension(extension) if extension else None

    if format_names & IMAGE_FORMAT_NAMES:
        return "image"

    if has_audio and not has_video:
        return "audio"

    if has_video:
        return "video"

    if has_subtitle:
        return "subtitle"

    return extension_kind


def _duration(value: str | None) -> float | None:
    """Parse ffprobe duration."""
    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None
