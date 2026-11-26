"""Optional local image generation (A1111 / ComfyUI detection only)."""
from fastapi import APIRouter, HTTPException

from .. import config, database
from ..models.schemas import ImageGenerateIn
from ..services import archive_service, image_service
from ..utils.files import new_id

router = APIRouter(tags=["images"])


@router.get("/images/status")
def images_status():
    return image_service.status()


@router.post("/images/generate")
def generate_image(payload: ImageGenerateIn):
    try:
        path = image_service.generate(payload.prompt, payload.negative_prompt,
                                      payload.width, payload.height, payload.steps)
    except image_service.ImageBackendUnavailable as e:
        raise HTTPException(503, str(e))
    media_id = new_id("m")
    probe = archive_service.probe_file(path)
    row = database.insert_media({
        "id": media_id, "project_id": payload.project_id, "scene_id": None,
        "original_name": path.name, "stored_name": path.name,
        "rel_path": f"images/{path.name}", "kind": "image",
        "size_bytes": path.stat().st_size, "width": probe.get("width"),
        "height": probe.get("height"),
        "description": f"Locally generated reference image. Prompt: {payload.prompt[:300]}",
        "created_at": database.now_iso(),
    })
    return {"media_id": media_id, "url": f"/api/media/{media_id}/file",
            "width": row["width"], "height": row["height"]}
