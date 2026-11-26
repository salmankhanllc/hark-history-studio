"""Safe file helpers: slugify, extension validation, path-traversal guards."""
import re
import uuid
from pathlib import Path

from .. import config


def new_id(prefix: str = "") -> str:
    return (prefix + uuid.uuid4().hex[:16]) if prefix else uuid.uuid4().hex[:16]


def slugify(text: str, fallback: str = "reel") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or fallback


def kind_for_ext(ext: str) -> str:
    ext = ext.lower()
    if ext in config.VIDEO_EXTS:
        return "video"
    if ext in config.IMAGE_EXTS:
        return "image"
    if ext in config.AUDIO_EXTS:
        return "audio"
    return "unknown"


def validate_media_ext(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in config.MEDIA_EXTS:
        raise ValueError(
            f"File type '{ext or '(none)'}' is not supported. "
            f"Allowed: {', '.join(sorted(config.MEDIA_EXTS))}"
        )
    return ext


def safe_resolve(base: Path, rel: str) -> Path:
    """Resolve rel under base and refuse anything that escapes base."""
    p = (base / rel).resolve()
    base_r = base.resolve()
    if p != base_r and base_r not in p.parents:
        raise ValueError("Path escapes the media directory")
    return p
