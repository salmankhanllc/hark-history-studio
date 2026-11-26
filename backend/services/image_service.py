"""Optional local image generation via a user-run Stable Diffusion backend.

Detects AUTOMATIC1111 (127.0.0.1:7860) and ComfyUI (127.0.0.1:8188).
Generation is only attempted when A1111 is actually running. This module
never fabricates an image: if nothing is running you get a clear error.
"""
import base64
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path

from .. import config
from ..utils.files import new_id

log = logging.getLogger("hark.image")

HELP = (
    "No local image-generation backend is running. Start AUTOMATIC1111 "
    "(--api flag) on port 7860 or ComfyUI on port 8188, then try again. "
    "Image generation is optional — the studio's core workflow uses real "
    "archival footage and does not need it."
)


class ImageBackendUnavailable(Exception):
    pass


def _get(url: str, timeout: float = 2.0):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def status() -> dict:
    a1111 = {"running": False, "models": [], "url": config.A1111_URL}
    try:
        models = _get(config.A1111_URL + "/sdapi/v1/sd-models")
        a1111["running"] = True
        a1111["models"] = [m.get("model_name", "") for m in models][:20]
    except Exception:
        pass
    comfy = {"running": False, "url": config.COMFYUI_URL}
    try:
        _get(config.COMFYUI_URL + "/system_stats")
        comfy["running"] = True
    except Exception:
        pass
    return {"a1111": a1111, "comfyui": comfy,
            "ready": a1111["running"], "help": None if a1111["running"] else HELP}


def generate(prompt: str, negative_prompt: str = "", width: int = 832,
             height: int = 1216, steps: int = 20) -> Path:
    st = status()
    if not st["a1111"]["running"]:
        raise ImageBackendUnavailable(HELP)
    body = json.dumps({
        "prompt": prompt, "negative_prompt": negative_prompt,
        "width": int(width), "height": int(height), "steps": int(steps),
        "sampler_name": "Euler a", "cfg_scale": 7,
    }).encode("utf-8")
    req = urllib.request.Request(config.A1111_URL + "/sdapi/v1/txt2img", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ImageBackendUnavailable(f"A1111 generation failed: {e}")
    images = data.get("images") or []
    if not images:
        raise ImageBackendUnavailable("A1111 returned no image.")
    out = config.IMAGES_DIR / f"img_{new_id()}.png"
    out.write_bytes(base64.b64decode(images[0]))
    return out
