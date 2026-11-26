"""Archive media helpers: ffprobe metadata + ffmpeg thumbnails."""
import json
import logging
import shutil
import subprocess
from pathlib import Path

from .. import config
from ..utils.files import kind_for_ext

log = logging.getLogger("hark.archive")


def ffmpeg_path():
    return shutil.which("ffmpeg")


def ffprobe_path():
    return shutil.which("ffprobe")


def probe_file(path: Path) -> dict:
    """Return {duration, width, height, video_codec, audio_codec} via ffprobe.
    Images get width/height; duration may be None."""
    info = {"duration": None, "width": None, "height": None,
            "video_codec": None, "audio_codec": None}
    probe = ffprobe_path()
    if not probe:
        return info
    try:
        out = subprocess.run(
            [probe, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=60)
        data = json.loads(out.stdout or "{}")
        fmt = data.get("format", {})
        if fmt.get("duration"):
            info["duration"] = float(fmt["duration"])
        for s in data.get("streams", []):
            if s.get("codec_type") == "video" and not info["video_codec"]:
                info["video_codec"] = s.get("codec_name")
                info["width"] = s.get("width")
                info["height"] = s.get("height")
                if info["duration"] is None and s.get("duration"):
                    info["duration"] = float(s["duration"])
            elif s.get("codec_type") == "audio" and not info["audio_codec"]:
                info["audio_codec"] = s.get("codec_name")
    except Exception as e:
        log.warning("ffprobe failed for %s: %s", path, e)
    return info


def make_thumbnail(src: Path, media_id: str, kind: str):
    """Create a JPEG poster in media/thumbs/. Returns project-relative path or None."""
    ff = ffmpeg_path()
    if not ff or kind not in ("video", "image"):
        return None
    out = config.THUMBS_DIR / f"{media_id}.jpg"
    try:
        if kind == "video":
            cmd = [ff, "-y", "-ss", "1", "-i", str(src),
                   "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", str(out)]
        else:
            cmd = [ff, "-y", "-i", str(src),
                   "-vf", "scale=360:-2", "-q:v", "4", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
            return f"thumbs/{media_id}.jpg"
    except Exception as e:
        log.warning("thumbnail failed for %s: %s", src, e)
    return None


def classify(filename: str) -> str:
    return kind_for_ext(Path(filename).suffix)
