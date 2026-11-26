"""Local voiceover (Piper TTS). Honest 503 when Piper/voices are absent."""
from fastapi import APIRouter, HTTPException

from .. import config, database
from ..models.schemas import TTSIn
from ..services import audio_service
from ..utils.files import new_id

router = APIRouter(tags=["audio"])


@router.get("/audio/status")
def audio_status():
    return audio_service.status()


@router.post("/audio/tts")
def synthesize(payload: TTSIn):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(400, "No narration text was provided.")
    if len(text) > 5000:
        raise HTTPException(400, "Narration text is too long (max 5000 characters per request).")
    try:
        wav_path = audio_service.synthesize(text, payload.voice, payload.speed)
    except audio_service.PiperUnavailable as e:
        raise HTTPException(503, str(e))
    media_id = new_id("m")
    rel = f"audio/{wav_path.name}"
    row = database.insert_media({
        "id": media_id, "project_id": payload.project_id, "scene_id": None,
        "original_name": wav_path.name, "stored_name": wav_path.name,
        "rel_path": rel, "kind": "audio",
        "size_bytes": wav_path.stat().st_size,
        "duration": audio_service.wav_duration(wav_path),
        "description": "Voiceover generated locally with Piper TTS",
        "created_at": database.now_iso(),
    })
    return {"media_id": media_id, "url": f"/api/media/{media_id}/file",
            "duration": row["duration"], "voice": payload.voice}
