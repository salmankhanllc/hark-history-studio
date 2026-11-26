"""Hark History Studio — local backend entry point.

Run from the project root:
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
(start.bat does exactly this.)
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, database
from .routers import audio, images, media, projects, render, scripts, system

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("hark.main")

database.init_db()

app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)

# Local tool: the studio page may be opened from file:// or from this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api")
app.include_router(scripts.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(render.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True, "app": config.APP_NAME, "version": config.APP_VERSION}


# Serve the studio frontend at / (API routes above take precedence).
app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="frontend")

log.info("%s v%s ready on http://%s:%d", config.APP_NAME, config.APP_VERSION,
         config.HOST, config.PORT)
