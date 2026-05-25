from typing import Literal


MediaKind = Literal["video", "audio", "image", "subtitle"]


class UnsupportedConversion(Exception):
    """Raised when the requested conversion is not supported."""


FORMAT_GROUPS: dict[MediaKind, dict[str, set[str]]] = {
    "video": {
        "inputs": {
            "3g2", "3gp", "asf", "avi", "divx", "dv", "f4v", "flv", "m2ts",
            "m4v", "mkv", "mov", "mp4", "mpeg", "mpg", "mts", "mxf", "ogv",
            "rm", "rmvb", "ts", "vob", "webm", "wmv",
        },
        "outputs": {"mp4", "webm", "mkv", "mov", "avi"},
    },
    "audio": {
        "inputs": {
            "aac", "ac3", "aif", "aiff", "amr", "ape", "au", "caf", "dts",
            "flac", "m4a", "mka", "mp2", "mp3", "oga", "ogg", "opus", "ra",
            "wav", "wma",
        },
        "outputs": {"mp3", "m4a", "aac", "ogg", "opus", "flac", "wav"},
    },
    "image": {
        "inputs": {
            "apng", "avif", "bmp", "dpx", "exr", "gif", "ico", "j2k", "jp2",
            "jpeg", "jpg", "pam", "pbm", "pcx", "pgm", "png", "ppm", "psd",
            "sgi", "tga", "tif", "tiff", "webp",
        },
        "outputs": {"png", "jpg", "webp", "gif", "bmp", "tiff"},
    },
    "subtitle": {
        "inputs": {"ass", "lrc", "sami", "sbv", "smi", "srt", "ssa", "sub", "vtt"},
        "outputs": {"srt", "vtt", "ass"},
    },
}

OUTPUT_GROUPS: dict[MediaKind, tuple[MediaKind, ...]] = {
    "video": ("video", "audio"),
    "audio": ("audio",),
    "image": ("image",),
    "subtitle": ("subtitle",),
}

EXTENSION_ALIASES = {
    "jpeg": "jpg",
    "tif": "tiff",
}


def normalize_format(value: str) -> str:
    """Normalize user-provided format names."""
    normalized = value.lower().strip().lstrip(".")
    return EXTENSION_ALIASES.get(normalized, normalized)


def kind_for_extension(extension: str) -> MediaKind | None:
    """Return a media kind for a known file extension."""
    normalized = normalize_format(extension)
    for kind, formats in FORMAT_GROUPS.items():
        if normalized in formats["inputs"]:
            return kind
    return None


def kind_for_target(target_format: str) -> MediaKind | None:
    """Return a media kind for a supported output format."""
    normalized = normalize_format(target_format)
    for kind, formats in FORMAT_GROUPS.items():
        if normalized in formats["outputs"]:
            return kind
    return None


def allowed_targets(source_kind: MediaKind) -> set[str]:
    """Return output formats available for a source media kind."""
    targets: set[str] = set()
    for kind in OUTPUT_GROUPS[source_kind]:
        targets.update(FORMAT_GROUPS[kind]["outputs"])
    return targets


def validate_conversion(
    source_kind: MediaKind,
    source_format: str | None,
    target_format: str,
    *,
    has_audio: bool,
) -> str:
    """Validate and normalize a requested conversion target."""
    normalized_target = normalize_format(target_format)
    target_kind = kind_for_target(normalized_target)

    if target_kind is None:
        raise UnsupportedConversion(f"Unsupported target format: {target_format}.")

    if normalized_target not in allowed_targets(source_kind):
        raise UnsupportedConversion(
            f"Cannot convert {source_kind} to {normalized_target}."
        )

    if target_kind == "audio" and source_kind == "video" and not has_audio:
        raise UnsupportedConversion("Cannot extract audio: source has no audio stream.")

    if source_format and normalize_format(source_format) == normalized_target:
        raise UnsupportedConversion(
            f"Source is already in {normalized_target.upper()} format."
        )

    return normalized_target


def frontend_format_config() -> dict[str, object]:
    """Return a JSON-friendly format config for the frontend."""
    groups = {
        kind: {
            "label": "Видео" if kind == "video" else
            "Аудио" if kind == "audio" else
            "Изображение" if kind == "image" else
            "Субтитры",
            "inputs": sorted(data["inputs"]),
            "outputs": sorted(data["outputs"]),
        }
        for kind, data in FORMAT_GROUPS.items()
    }

    return {
        "groups": groups,
        "output_groups": {
            kind: list(targets)
            for kind, targets in OUTPUT_GROUPS.items()
        },
        "aliases": EXTENSION_ALIASES,
    }
