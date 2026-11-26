"""Script generation endpoint (template engine + optional local Ollama)."""
from fastapi import APIRouter

from ..models.schemas import ScriptGenerateIn
from ..services import script_service
from ..services.scene_service import ordering_report

router = APIRouter(tags=["scripts"])


@router.post("/scripts/generate")
def generate_script(payload: ScriptGenerateIn):
    result = script_service.generate(payload.topic, payload.hook, payload.date,
                                     payload.detail, payload.style)
    result["ordering"] = ordering_report(result["scenes"])
    return result
