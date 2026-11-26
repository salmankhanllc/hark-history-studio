"""System status: honest detection of every local dependency."""
import platform
import shutil
import sys

from fastapi import APIRouter

from .. import config
from ..services import archive_service, audio_service, image_service, script_service

router = APIRouter(tags=["system"])


def _tool_version(path, args=("--version",)):
    if not path:
        return None
    try:
        import subprocess
        out = subprocess.run([path, *args], capture_output=True, text=True, timeout=10)
        line = (out.stdout or out.stderr or "").strip().splitlines()
        return line[0] if line else None
    except Exception:
        return None


@router.get("/system/status")
def system_status():
    ff = archive_service.ffmpeg_path()
    fp = archive_service.ffprobe_path()
    ollama = script_service.ollama_status()
    piper = audio_service.status()
    images = image_service.status()
    disk = shutil.disk_usage(str(config.PROJECT_ROOT))
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": platform.platform(),
        "ffmpeg": {"available": bool(ff), "path": ff, "version": _tool_version(ff, ("-version",))},
        "ffprobe": {"available": bool(fp), "path": fp, "version": _tool_version(fp)},
        "ollama": ollama,
        "piper": {"installed": piper["piper"]["installed"], "kind": piper["piper"]["kind"],
                  "voices": piper["voices"], "ready": piper["ready"], "help": piper["help"]},
        "image_generation": images,
        "video_generation": {"available": False,
                             "note": "AI video generation was removed from this studio by design. "
                                     "The workflow uses real archival footage that you upload."},
        "disk": {"free_gb": round(disk.free / 1e9, 1), "total_gb": round(disk.total / 1e9, 1)},
        "database": str(config.DB_PATH),
    }
