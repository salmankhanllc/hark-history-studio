"""Scene normalisation and ordering checks, shared by the script service
and the projects router."""
from ..utils.files import new_id

VALID_KINDS = {"firing", "impact", "aftermath", "scene"}


def build_prompt(core: dict, st: dict) -> str:
    """The studio's locked 8-part prompt anatomy (same as the frontend engine)."""
    return (
        "Vertical 9:16, 1080x1920. "
        f"SUBJECT: {core.get('subject', '')}. "
        f"ACTION: {core.get('action', '')}. "
        f"ENVIRONMENT: {core.get('environment', '')}. "
        f"PERIOD DETAILS: {core.get('period', '')}. "
        f"LIGHTING: {core.get('lighting', '')}. "
        f"CAMERA: {core.get('camera', '')}. "
        f"GRADE: {st.get('grade', '')}; {st.get('colour', '')}. "
        f"LOOK: {st.get('look', '')}. "
        f"NEGATIVES: {st.get('rules', '')}; no watermarks, no subtitles, no logos."
    )


def normalize_scenes(raw_scenes: list, topic: str, st: dict) -> list:
    scenes = []
    for i, r in enumerate(raw_scenes or []):
        duration = r.get("duration") or 4
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = 4
        duration = min(8.0, max(2.0, duration))
        kind = r.get("kind") or "scene"
        if kind not in VALID_KINDS:
            kind = "scene"
        prompt = r.get("prompt") or ""
        if len(prompt) < 80:
            core = {
                "subject": r.get("subject") or r.get("title") or f"Scene {i + 1}",
                "action": r.get("action", ""), "environment": r.get("environment", ""),
                "period": r.get("period", ""), "lighting": r.get("lighting", ""),
                "camera": r.get("camera", ""),
            }
            prompt = build_prompt(core, st)
        scenes.append({
            "id": r.get("id") or new_id("s"),
            "n": i + 1,
            "title": r.get("title") or f"Scene {i + 1}",
            "duration": duration,
            "shotType": r.get("shotType") or r.get("shot_type") or "Scene",
            "kind": kind,
            "camera": r.get("camera", ""),
            "narration": r.get("narration", ""),
            "soundCue": r.get("soundCue") or r.get("sound_cue", ""),
            "searchTerm": r.get("searchTerm") or r.get("search_term") or f"{topic} {r.get('title', '')}".strip(),
            "prompt": prompt,
            "mediaId": r.get("mediaId"),
            "trimStart": r.get("trimStart") or 0,
        })
    return scenes


def ordering_report(scenes: list) -> dict:
    """Firing must be followed immediately by impact; aftermath last."""
    firing_impact = any(
        scenes[i].get("kind") == "firing" and scenes[i + 1].get("kind") == "impact"
        for i in range(len(scenes) - 1)
    )
    aftermath_last = bool(scenes) and scenes[-1].get("kind") == "aftermath"
    return {"firing_then_impact": firing_impact, "aftermath_last": aftermath_last,
            "ok": firing_impact and aftermath_last}
