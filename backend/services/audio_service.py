"""Local voiceover via Piper TTS (fully offline, open source).

Detection order:
1. `piper` executable on PATH
2. the venv's python module:  python -m piper
3. importable `piper` python package

Voices are .onnx files (with a matching .onnx.json) in models/piper/.
If Piper or voices are missing, callers get a clear, honest error with
install instructions — never a fake audio file.
"""
import logging
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from .. import config

log = logging.getLogger("hark.audio")

INSTALL_HELP = (
    "Piper TTS is not installed. To enable offline voiceovers: "
    "1) In the studio folder run: .venv\\Scripts\\pip install piper-tts  (Windows) "
    "or .venv/bin/pip install piper-tts (Linux/macOS). "
    "2) Download a voice (.onnx + .onnx.json) from "
    "https://huggingface.co/rhasspy/piper-voices and put both files in the models/piper/ folder. "
    "3) Restart the backend."
)


class PiperUnavailable(Exception):
    pass


def find_piper() -> dict:
    exe = shutil.which("piper")
    if exe:
        return {"installed": True, "kind": "cli", "path": exe}
    try:
        r = subprocess.run([sys.executable, "-m", "piper", "--help"],
                           capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            return {"installed": True, "kind": "module", "path": f"{sys.executable} -m piper"}
    except Exception:
        pass
    try:
        import piper  # noqa: F401
        return {"installed": True, "kind": "python", "path": "python:piper"}
    except Exception:
        pass
    return {"installed": False, "kind": None, "path": None}


def list_voices() -> list:
    voices = []
    for onnx in sorted(config.PIPER_MODELS_DIR.glob("*.onnx")):
        voices.append({
            "name": onnx.stem,
            "file": onnx.name,
            "has_config": (config.PIPER_MODELS_DIR / (onnx.name + ".json")).exists(),
        })
    return voices


def status() -> dict:
    p = find_piper()
    voices = list_voices()
    return {"piper": p, "voices": voices,
            "ready": bool(p["installed"] and voices),
            "help": None if (p["installed"] and voices) else INSTALL_HELP}


def _wav_duration(path: Path):
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


def synthesize(text: str, voice: str = None, speed: float = 1.0) -> Path:
    """Synthesize text to a WAV in media/audio/. Raises PiperUnavailable."""
    st = status()
    if not st["piper"]["installed"]:
        raise PiperUnavailable(INSTALL_HELP)
    voices = st["voices"]
    if not voices:
        raise PiperUnavailable(
            "Piper is installed but no voice models were found. Download a voice "
            "(.onnx + .onnx.json) from https://huggingface.co/rhasspy/piper-voices "
            "into the models/piper/ folder, then try again.")
    chosen = None
    if voice:
        chosen = next((v for v in voices if v["name"] == voice or v["file"] == voice), None)
    if not chosen:
        chosen = voices[0]
    model_path = config.PIPER_MODELS_DIR / chosen["file"]
    length_scale = 1.0 / max(0.5, min(2.0, speed or 1.0))

    from ..utils.files import new_id
    out_path = config.AUDIO_DIR / f"voice_{new_id()}.wav"

    kind = st["piper"]["kind"]
    if kind in ("cli", "module"):
        cmd = ([shutil.which("piper")] if kind == "cli" else [sys.executable, "-m", "piper"])
        cmd += ["--model", str(model_path), "--output_file", str(out_path),
                "--length-scale", f"{length_scale:.3f}"]
        r = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise PiperUnavailable(f"Piper failed: {(r.stderr or r.stdout or '').strip()[:400]}")
    else:  # python API
        try:
            from piper import PiperVoice
            from piper.config import SynthesisConfig
            v = PiperVoice.load(str(model_path))
            with wave.open(str(out_path), "wb") as wav_file:
                v.synthesize_wav(text, wav_file,
                                 syn_config=SynthesisConfig(length_scale=length_scale))
        except Exception as e:
            raise PiperUnavailable(f"Piper Python API failed: {e}")
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise PiperUnavailable("Piper produced no audio output.")
    return out_path


def wav_duration(path: Path):
    return _wav_duration(path)
