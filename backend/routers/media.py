"""Archive media: upload, probe, thumbnail, organise, serve, delete."""
import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import config, database
from ..models.schemas import MediaUpdateIn
from ..services import archive_service
from ..utils.files import (kind_for_ext, new_id, safe_resolve,
                           validate_media_ext)

log = logging.getLogger("hark.media")
router = APIRouter(tags=["media"])


def _public(row: dict) -> dict:
    out = dict(row)
    out["url"] = f"/api/media/{row['id']}/file"
    out["thumb_url"] = f"/api/media/{row['id']}/thumb" if row.get("thumb_rel_path") else None
    return out


@router.post("/media/upload")
async def upload_media(file: UploadFile = File(...),
                       project_id: str = Form(None),
                       scene_id: str = Form(None)):
    try:
        ext = validate_media_ext(file.filename or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    media_id = new_id("m")
    stored_name = f"{media_id}{ext}"
    dest = config.UPLOADS_DIR / stored_name
    size = 0
    try:
        with open(dest, "wb") as fh:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    fh.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"File exceeds the {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
                fh.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(500, f"Upload failed: {e}")
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Uploaded file was empty.")

    kind = kind_for_ext(ext)
    probe = archive_service.probe_file(dest) if kind in ("video", "image") else {}
    thumb_rel = archive_service.make_thumbnail(dest, media_id, kind)
    row = database.insert_media({
        "id": media_id, "project_id": project_id, "scene_id": scene_id,
        "original_name": file.filename, "stored_name": stored_name,
        "rel_path": f"uploads/{stored_name}", "kind": kind, "size_bytes": size,
        "duration": probe.get("duration"), "width": probe.get("width"),
        "height": probe.get("height"), "thumb_rel_path": thumb_rel,
        "created_at": database.now_iso(),
    })
    log.info("Uploaded media %s (%s, %d bytes)", media_id, kind, size)
    return _public(row)


@router.get("/media")
def list_media(project_id: str = None):
    return {"media": [_public(r) for r in database.list_media(project_id)]}


@router.get("/media/{media_id}")
def get_media(media_id: str):
    row = database.get_media(media_id)
    if not row:
        raise HTTPException(404, "Media not found")
    return _public(row)


@router.patch("/media/{media_id}")
def update_media(media_id: str, payload: MediaUpdateIn):
    if not database.get_media(media_id):
        raise HTTPException(404, "Media not found")
    row = database.update_media(media_id, payload.model_dump())
    return _public(row)


@router.delete("/media/{media_id}")
def delete_media(media_id: str):
    row = database.get_media(media_id)
    if not row:
        raise HTTPException(404, "Media not found")
    try:
        safe_resolve(config.MEDIA_DIR, row["rel_path"]).unlink(missing_ok=True)
        if row.get("thumb_rel_path"):
            safe_resolve(config.MEDIA_DIR, row["thumb_rel_path"]).unlink(missing_ok=True)
    except ValueError:
        pass
    database.delete_media(media_id)
    return {"deleted": media_id}


@router.get("/media/{media_id}/file")
def media_file(media_id: str):
    row = database.get_media(media_id)
    if not row:
        raise HTTPException(404, "Media not found")
    try:
        path = safe_resolve(config.MEDIA_DIR, row["rel_path"])
    except ValueError:
        raise HTTPException(400, "Invalid media path")
    if not path.exists():
        raise HTTPException(404, "Media file is missing from disk")
    return FileResponse(str(path), filename=row["original_name"])


@router.get("/media/{media_id}/thumb")
def media_thumb(media_id: str):
    row = database.get_media(media_id)
    if not row or not row.get("thumb_rel_path"):
        raise HTTPException(404, "No thumbnail for this media")
    path = safe_resolve(config.MEDIA_DIR, row["thumb_rel_path"])
    if not path.exists():
        raise HTTPException(404, "Thumbnail missing from disk")
    return FileResponse(str(path), media_type="image/jpeg")
