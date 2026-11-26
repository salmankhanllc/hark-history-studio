"""Render jobs (background) + export downloads."""
import logging
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import config, database
from ..models.schemas import RenderIn
from ..services import render_service
from ..utils import jobs
from ..utils.files import new_id, safe_resolve

log = logging.getLogger("hark.render.router")
router = APIRouter(tags=["render"])


@router.post("/render/jobs")
def create_render_job(payload: RenderIn):
    project = database.get_project(payload.project_id)
    if not project:
        raise HTTPException(404, "Project not found — save the project to the backend first.")
    settings = payload.model_dump()
    job_id = new_id("j")
    jobs.create(job_id, "render")

    def _run():
        try:
            render_service.render_project(job_id, project, settings)
        except render_service.RenderError as e:
            jobs.update(job_id, status="error", error=str(e), message="Render failed")
        except Exception as e:  # never leave a job hanging
            log.exception("Render job %s crashed", job_id)
            jobs.update(job_id, status="error", error=f"Unexpected error: {e}",
                        message="Render failed")

    threading.Thread(target=_run, daemon=True, name=f"render-{job_id}").start()
    return {"job_id": job_id, "status": "queued"}


@router.get("/render/jobs/{job_id}")
def get_render_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found (jobs are kept in memory; it may predate a backend restart)")
    return job


@router.get("/exports")
def list_exports(project_id: str = None):
    return {"exports": database.list_exports(project_id)}


@router.get("/exports/{export_id}/download")
def download_export(export_id: str):
    row = database.get_export(export_id)
    if not row:
        raise HTTPException(404, "Export not found")
    try:
        path = safe_resolve(config.EXPORTS_DIR, row["rel_path"])
    except ValueError:
        raise HTTPException(400, "Invalid export path")
    if not path.exists():
        raise HTTPException(404, "Export file is missing from disk")
    return FileResponse(str(path), media_type="video/mp4", filename=row["filename"])
