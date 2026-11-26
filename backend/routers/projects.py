"""Project CRUD backed by SQLite."""
from fastapi import APIRouter, HTTPException

from .. import database
from ..models.schemas import ProjectIn
from ..utils.files import new_id

router = APIRouter(tags=["projects"])


@router.get("/projects")
def list_projects():
    return {"projects": database.list_projects()}


@router.post("/projects")
def save_project(payload: ProjectIn):
    project = payload.model_dump()
    if not project.get("id"):
        project["id"] = new_id("p")
    # Scene models back to plain dicts (already are via model_dump)
    saved = database.upsert_project(project)
    saved["backendId"] = saved["id"]
    return saved


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    project = database.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    project["backendId"] = project["id"]
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    if not database.delete_project(project_id):
        raise HTTPException(404, "Project not found")
    return {"deleted": project_id}


@router.get("/projects/{project_id}/exports")
def project_exports(project_id: str):
    if not database.get_project(project_id):
        raise HTTPException(404, "Project not found")
    return {"exports": database.list_exports(project_id)}
