"""Pydantic request models. Extra fields are allowed so the frontend's
project JSON round-trips losslessly."""
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SceneIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: Optional[str] = None
    n: int = 0
    title: str = ""
    duration: float = 4
    shotType: str = "Scene"
    kind: str = "scene"
    camera: str = ""
    narration: str = ""
    soundCue: str = ""
    searchTerm: str = ""
    prompt: str = ""
    mediaId: Optional[str] = None
    trimStart: float = 0


class ProjectIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: Optional[str] = None
    topic: str = ""
    hook: str = ""
    date: str = ""
    detail: str = ""
    styleName: str = ""
    createdAt: Optional[str] = None
    scenes: list[SceneIn] = Field(default_factory=list)


class ScriptGenerateIn(BaseModel):
    topic: str
    hook: str = ""
    date: str = ""
    detail: str = ""
    style: Optional[dict[str, Any]] = None


class MediaUpdateIn(BaseModel):
    tags: Optional[str] = None
    description: Optional[str] = None
    source_info: Optional[str] = None
    scene_id: Optional[str] = None
    project_id: Optional[str] = None


class TTSIn(BaseModel):
    text: str
    voice: Optional[str] = None
    speed: float = 1.0
    project_id: Optional[str] = None


class ImageGenerateIn(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 832
    height: int = 1216
    steps: int = 20
    project_id: Optional[str] = None


class RenderIn(BaseModel):
    project_id: str
    orientation: str = "9:16"
    narration_media_id: Optional[str] = None
    music_media_id: Optional[str] = None
    narration_volume: float = 1.0
    music_volume: float = 0.3
    clip_volume: float = 1.0
    use_clip_audio: bool = True
