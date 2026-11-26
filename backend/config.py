"""Central configuration for the History Studio local backend.

Everything is local: no API keys, no cloud services. Paths are resolved
relative to the project root (the folder that contains backend/).
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

FRONTEND_DIR = PROJECT_ROOT / "frontend"
MEDIA_DIR = PROJECT_ROOT / "media"
UPLOADS_DIR = MEDIA_DIR / "uploads"
THUMBS_DIR = MEDIA_DIR / "thumbs"
AUDIO_DIR = MEDIA_DIR / "audio"
IMAGES_DIR = MEDIA_DIR / "images"
PROJECTS_DIR = PROJECT_ROOT / "projects"
EXPORTS_DIR = PROJECT_ROOT / "exports"
MODELS_DIR = PROJECT_ROOT / "models"
PIPER_MODELS_DIR = MODELS_DIR / "piper"
FONTS_DIR = BACKEND_DIR / "assets" / "fonts"
DB_PATH = PROJECTS_DIR / "hark_studio.db"

HOST = os.environ.get("HARK_HOST", "127.0.0.1")
PORT = int(os.environ.get("HARK_PORT", "8765"))

MAX_UPLOAD_BYTES = int(os.environ.get("HARK_MAX_UPLOAD_MB", "2048")) * 1024 * 1024

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg"}
MEDIA_EXTS = VIDEO_EXTS | IMAGE_EXTS

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
A1111_URL = os.environ.get("A1111_URL", "http://127.0.0.1:7860")
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")

APP_NAME = "History Studio — Local Backend"
APP_VERSION = "2.0.0"


def ensure_dirs() -> None:
    for d in (MEDIA_DIR, UPLOADS_DIR, THUMBS_DIR, AUDIO_DIR, IMAGES_DIR,
              PROJECTS_DIR, EXPORTS_DIR, MODELS_DIR, PIPER_MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)


ensure_dirs()
