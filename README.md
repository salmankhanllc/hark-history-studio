# History Studio — Local Backend Edition

A fully local historical documentary video studio. It plans style-locked
reels, organises your real archival footage, and renders true MP4 videos
with FFmpeg — **entirely on your own machine**.

- **No paid APIs. No API keys. No accounts. No cloud.**
- **No AI video generation** — removed by design. Every clip in a finished
  reel is real footage that you found, checked and uploaded yourself.
- Core workflow runs **offline** after the one-time install (pip needs the
  internet once to download the Python packages).

Tested with **Python 3.12.3**, FFmpeg 8.1.2, Windows-style `.bat` launchers
included. Any Python 3.11+ works.

---

## Quick start (Windows)

1. **Extract the zip first** into its own folder (e.g. `Documents\history-studio-local`).
   Do NOT run anything from inside the zip.
2. Double-click **`install.bat`** — once. It checks for a real Python,
   builds `.venv`, installs the dependencies, tries the optional Piper
   voiceover engine, and checks for FFmpeg.
3. Double-click **`start.bat`** — the studio opens in your browser at
   **http://127.0.0.1:8765**. Keep the black window open while you work;
   close it to stop the studio.

### Windows preflight (run this first if install.bat complains)

Open Command Prompt in the extracted folder and run:

```
python --version
```

It must print a real version such as `Python 3.12.3`. If the Microsoft
Store opens instead, your Python is the Store stub — install the real one
from https://www.python.org/downloads/ and tick **“Add python.exe to PATH”**.

### FFmpeg (required for rendering)

If install.bat warns that FFmpeg is missing:

```
winget install Gyan.FFmpeg
```

or download a build from https://www.gyan.dev/ffmpeg/builds/ and add its
`bin` folder to PATH. Restart `start.bat` afterwards.

### Linux / macOS

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements-tts.txt   # optional voiceovers
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Then open http://127.0.0.1:8765.

---

## How the studio works

1. **Setup** — load the Battle of Britain reference style (or keep the
   default). The *Local Backend* panel shows what is actually available on
   your machine: Python, FFmpeg, Ollama, Piper, image generation.
2. **Create** — type Topic (title L1), Hook (L2), Date (L3) and story
   detail, then **Generate Scenes**. Scenes come from the local backend:
   a local Ollama model if you run one, otherwise the built-in offline
   template engine. The mode used is always labelled — nothing is faked.
   Scenes are ordered firing → impact, aftermath last, each with the full
   8-part prompt, narration note, combat sound cue and 9 free archive
   search links.
3. **Footage** — find the real archival clip with the per-scene links,
   download it, enhance it with the 8-step recipe on the card, and upload
   it onto the scene card. Uploads are stored by the backend
   (`media/uploads/`) with ffprobe metadata and a thumbnail.
4. **Voiceover (optional)** — *Generate Voiceover (Local TTS)* speaks the
   scenes' narration lines with Piper and mixes them into the MP4.
5. **Export** — *Export MP4 (Local Backend)* renders a real
   1080×1920 H.264/AAC MP4: footage in the locked window, black bars,
   L1 white from 0s, L2 gold fading in at ~7s, L3 typewriter from ~15.5s,
   titles measured and stacked with the bundled Anton font. Progress is
   shown live; the finished file lands in `exports/` and in the export
   history. The browser WebM export still works too (no audio mix).
6. **Library** — the browser Library keeps quick local copies; the
   **Server Library** stores projects in SQLite (`projects/hark_studio.db`)
   with their media and exports, so work survives browser clears.

## Supported offline features

| Feature | Works offline | Needs |
|---|---|---|
| Scene/script generation (template engine) | ✅ | nothing |
| Scene generation with a local LLM | ✅ | Ollama + a pulled model (optional) |
| Project storage (SQLite), reopen projects | ✅ | nothing |
| Media upload, probing, thumbnails, tags | ✅ | FFmpeg/ffprobe |
| Reel Preview + Quality Checklist (browser) | ✅ | nothing |
| Browser WebM export | ✅ | nothing |
| **MP4 render (titles, mixing, progress)** | ✅ | FFmpeg |
| Voiceover (Piper TTS) | ✅ | Piper + a voice in `models/piper/` |
| Reference image generation | ✅ | A1111 or ComfyUI running locally (optional) |
| AI video generation | ❌ | **Removed by design** |

## Optional local AI models — honest requirements

- **Ollama (script writing)** — install from https://ollama.com, then
  `ollama pull llama3.1` (≈5 GB). The backend detects it automatically at
  http://127.0.0.1:11434. Without it, the template engine writes scripts —
  labelled as such.
- **Piper TTS (voiceover)** — `requirements-tts.txt` installs the engine.
  One English voice (`en_US-lessac-low`, 63 MB) is bundled in
  `models/piper/`. More voices: https://huggingface.co/rhasspy/piper-voices
  (drop the `.onnx` + `.onnx.json` pair into `models/piper/`).
  CPU-only, fast, fully offline.
- **Stable Diffusion (reference images)** — if AUTOMATIC1111 runs locally
  with `--api` (port 7860), the backend can generate reference images via
  `/api/images/generate`. ComfyUI (port 8188) is detected for status.
  A GPU with 6–8 GB+ VRAM is realistically required; this is optional and
  never blocks the core workflow.
- **Video generation models** — intentionally **not** part of this studio.

## Project layout

```
backend/            FastAPI app (main.py, config.py, database.py)
  models/           Pydantic schemas
  routers/          system, scripts, projects, media, audio, images, render
  services/         script/scene, archive, audio (Piper), image, render (FFmpeg)
  utils/            safe file helpers, background job registry
  assets/fonts/     Anton (bundled) + Liberation Sans Bold fallback
frontend/           The studio page (index.html) — same design as before
models/piper/       Piper voice models (.onnx + .onnx.json)
media/              uploads/, thumbs/, audio/, images/  (your footage)
projects/           hark_studio.db (SQLite)
exports/            finished MP4 renders
tests/              smoke_test.py — end-to-end API + render test
install.bat         one-time Windows install (probes real Python)
start.bat           Windows launcher → http://127.0.0.1:8765
```

## API (for the curious)

`GET /api/system/status` · `POST /api/scripts/generate` ·
`GET/POST/DELETE /api/projects` · `POST /api/media/upload`,
`GET/PATCH/DELETE /api/media/{id}` · `GET /api/audio/status`,
`POST /api/audio/tts` · `GET /api/images/status`, `POST /api/images/generate` ·
`POST /api/render/jobs`, `GET /api/render/jobs/{id}` ·
`GET /api/exports`, `GET /api/exports/{id}/download`

## Notes & limits

- Render jobs live in memory: restarting the backend forgets a running
  job's status (finished files stay in `exports/` and in the database).
- Uploads are capped at 2 GB per file (configurable via `HARK_MAX_UPLOAD_MB`).
- Uploaded footage is **your** responsibility to clear for use — the studio
  never claims any clip is public domain.
- The studio binds to 127.0.0.1 only. It is a single-user local tool.
