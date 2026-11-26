# Local models

## Piper TTS voices → `piper/`

The downloadable studio zip bundles one English voice
(`en_US-lessac-low.onnx` + `.onnx.json`, 63 MB) so voiceovers work out of
the box. The voice is **not** stored in this GitHub repo — the GitHub
contents API rejects files that large.

To add it (or any other voice) to a repo checkout:

1. Download the `.onnx` and `.onnx.json` pair from
   https://huggingface.co/rhasspy/piper-voices
   (e.g. `en/en_US/lessac/low/en_US-lessac-low.onnx`).
2. Put both files in `models/piper/`.
3. Restart the backend — Setup → Local Backend will show Piper as ready.

## Ollama (script writing, optional)

No files needed here. Install Ollama (https://ollama.com), run
`ollama pull llama3.1`, and the backend detects it automatically at
http://127.0.0.1:11434. Without it, the built-in offline template engine
writes the scripts and says so.

## Stable Diffusion (reference images, optional)

Nothing is stored in this folder. If AUTOMATIC1111 runs locally with the
`--api` flag (port 7860), the backend uses it for reference images.
ComfyUI (port 8188) is detected for status only.

## Video generation models

None — AI video generation was removed from this studio by design.
Finished reels are assembled from real archival footage you upload.
