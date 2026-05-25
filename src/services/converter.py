import asyncio
import os
import signal
from dataclasses import dataclass
from pathlib import Path

from src.core.config import settings
from src.services.formats import kind_for_target, normalize_format


class ConversionError(Exception):
    """Raised when ffmpeg conversion fails."""


@dataclass(frozen=True)
class ResourceProfile:
    """Process-level conversion limits for a plan tier."""

    threads: int
    nice: int
    timeout_seconds: int


def get_resource_profile(plan_tier: str) -> ResourceProfile:
    """Return FFmpeg process limits for a plan tier."""
    if plan_tier == "pro":
        return ResourceProfile(
            threads=settings.pro_ffmpeg_threads,
            nice=settings.pro_process_nice,
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )

    return ResourceProfile(
        threads=settings.free_ffmpeg_threads,
        nice=settings.free_process_nice,
        timeout_seconds=settings.ffmpeg_timeout_seconds,
    )


async def convert(
    input_path: Path,
    output_path: Path,
    target_format: str,
    plan_tier: str,
) -> None:
    """Convert a file using ffmpeg."""
    profile = get_resource_profile(plan_tier)
    command = _build_command(input_path, output_path, target_format, profile)

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            preexec_fn=_nice_process(profile.nice),
        )
    except OSError as e:
        raise ConversionError(f"Cannot start ffmpeg: {e}") from e

    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=profile.timeout_seconds,
        )
    except asyncio.TimeoutError as e:
        await _terminate_process_group(process)
        output_path.unlink(missing_ok=True)
        raise ConversionError("Conversion timed out.") from e

    if process.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise ConversionError(_error_message(stderr))


def _build_command(
    input_path: Path,
    output_path: Path,
    target_format: str,
    profile: ResourceProfile,
) -> list[str]:
    """Build a constrained ffmpeg command."""
    normalized_target = normalize_format(target_format)
    command = [
        settings.ffmpeg_path,
        "-hide_banner",
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-i", str(input_path),
    ]

    command.extend(_target_options(normalized_target, profile))
    command.append(str(output_path))
    return command


def _target_options(target_format: str, profile: ResourceProfile) -> list[str]:
    """Return conservative FFmpeg options for a target format."""
    target_kind = kind_for_target(target_format)

    if target_kind == "audio":
        return ["-vn", "-threads", str(profile.threads)]

    if target_kind == "video":
        return ["-map", "0:v:0", "-map", "0:a?", "-threads", str(profile.threads)]

    if target_kind == "image":
        return ["-frames:v", "1", "-threads", str(profile.threads)]

    if target_kind == "subtitle":
        return []

    raise ConversionError(f"Unsupported target format: {target_format}.")


def _nice_process(nice: int):
    """Return a child-process hook that lowers CPU priority."""
    if nice <= 0:
        return None

    def apply_nice() -> None:
        os.nice(nice)

    return apply_nice


async def _terminate_process_group(process: asyncio.subprocess.Process) -> None:
    """Terminate a process group started for FFmpeg."""
    if process.returncode is not None:
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        await process.wait()


def _error_message(stderr: bytes) -> str:
    """Create a short user-facing FFmpeg error."""
    text = stderr.decode(errors="replace").strip()
    if not text:
        return "ffmpeg failed without an error message."
    return text[-2000:]
