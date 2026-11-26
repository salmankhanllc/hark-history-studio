# Test Report — Hark History Studio, Local Backend Edition

All tests below were **actually run** on 2026-11-26 on this machine
(Linux, Python 3.12.3, FFmpeg 8.1.2). Nothing here is simulated.

## Environment

- Python 3.12.3 · pip installed into a project venv without errors:
  FastAPI 0.165.0, Uvicorn 0.54.0, Pydantic 2.14.4, python-multipart 0.0.34,
  Pillow 13.0.0; optional Piper TTS 1.8.0 (onnxruntime) also installed.
- FFmpeg / ffprobe 8.1.2 detected on PATH.
- Anton font: downloaded from the google/fonts GitHub repo
  (Anton-Regular.ttf, 170,812 bytes, verified TrueType) and bundled in
  `backend/assets/fonts/`; Liberation Sans Bold bundled as fallback.

## Endpoint tests (live server, curl)

| Check | Result |
|---|---|
| `GET /api/health` | ✅ `{"ok": true, ...}` |
| `GET /api/system/status` | ✅ honest: ffmpeg/ffprobe found; Ollama **not running**; Piper ready; A1111/ComfyUI **not running**; video generation reported as removed |
| `POST /api/scripts/generate` | ✅ mode `"template"` (no Ollama on this machine), 6 scenes, 25 s total, ordering check `firing_then_impact: true, aftermath_last: true`; full 8-part prompts (~1,100 chars each) |
| `POST /api/projects` + `GET /api/projects/{id}` | ✅ save + reopen, 3 scenes intact |
| `DELETE /api/projects/{id}` | ✅ deleted |
| `POST /api/media/upload` (MP4 1280×736, MP4 1080×1920, PNG 1080×1920) | ✅ probed (codec, size, duration), thumbnail generated |
| Upload of a `.txt` file | ✅ rejected, HTTP 400 with the allowed-extension list |
| `PATCH /api/media/{id}` | ✅ tags + source_info saved |
| `DELETE /api/media/{id}` | ✅ row + file removed |
| `GET /api/audio/status` | ✅ Piper detected (python module), voice `en_US-lessac-low` listed |
| `POST /api/audio/tts` | ✅ real WAV synthesized: 4.34 s for the test line, registered as media |
| `POST /api/images/generate` with no SD backend running | ✅ honest HTTP 503 with setup instructions — no fake image |
| `GET /api/exports`, `GET /api/exports/{id}/download` | ✅ 4 exports listed; download returned 200 `video/mp4`, 11,929,250 bytes |

## Render tests (the core)

Test project "FALL OF DUNKIRK / GREAT ESCAPE IS OVER / JUNE 4, 1940",
3 scenes (7 s + 7 s + 6 s = 20 s) using the SANA airfield test clip
(scene 1, looped, silent source) and the Dunkirk archive demo
(scenes 2–3 with trimStart 1 s / 13 s, clip audio kept).

**9:16 render — `fall-of-dunkirk_f74ef8.mp4`**
- ffprobe: **1080×1920, H.264, 30 fps, AAC 48,000 Hz, 20.0 s**, faststart
  verified (moov at byte 36, before mdat).
- Title stack measured with PIL textbbox: bottom at **400 px inside the
  503 px top bar**; font reported as "Anton (bundled)".
- Stills extracted at 1 s / 8 s / 17 s / 19.5 s and inspected visually:
  - 1 s — L1 white only, top bar only, footage window clean. ✅
  - 8 s — L1 + gold L2 beneath it with a clear gap, no overlap. ✅
  - 17 s / 19.5 s — all three lines stacked with clear gaps; L3 fully
    typed (12 chars at 14 chars/s from 15.5 s completes ≈16.4 s). ✅

**Narration mix — `fall-of-dunkirk_33450f.mp4`**
- Same project + the Piper WAV mixed in. Volume proof (first 5 s, where
  scene 1's source clip is silent): plain render mean **−91.0 dB**
  (digital silence) vs narration render mean **−17.6 dB**, max −2.9 dB. ✅

**Missing-media error**
- A project whose scenes have no media fails the job with:
  “Scenes missing media: 1, 2. Upload footage for every scene, then
  export again.” ✅

**16:9 render — found and fixed a real bug**
- First 16:9 render put the title stack at bottom **443 px in a 300 px
  bar** — L2/L3 spilled onto the footage (verified on a still).
- Fix: title scale now follows bar height as well as canvas width
  (30-step shrink loop until the measured stack fits).
- Re-render `fall-of-dunkirk_984af5.mp4`: stack bottom **271 px ≤ 284 px**;
  still at 17 s inspected — all three lines fully inside the black bar
  with clear gaps. ✅ The 9:16 layout is unchanged (bottom 400 px,
  sizes 150/96/64).

## Frontend tests

- 36 anchored edits applied to sal's current studio file (each anchor
  asserted to match exactly once). Removed: OpenAI/Fal key fields and
  handlers, Quality Preset video-model radios, per-scene Generate Video
  buttons, Generate All Videos, `genSANA`, `genFal`, `openaiScenes`,
  `generateVideo` — grep for `fal.run`, `hf.space`, `api.openai.com`,
  `SANA_URL`, `FAL_MODELS`, `genSANA`, `genFal`, `openaiScenes`,
  `generateVideo` returns **0 matches**.
- Both `<script>` blocks extracted and passed **`node --check`** (Node v24.22.1).
- The page is served by the backend at `/` and still opens standalone
  from `file://` (backend calls fail soft: demo engine + WebM export +
  browser Library keep working; the Setup panel explains how to start
  the backend).

## Fresh-folder package test (as the user will run it)

- Zipped the cleaned project (≈58.7 MB; excludes `.venv`,
  test media, the test database and sample exports; includes the bundled
  Piper voice). The final shipped zip — identical except for this report
  file — was extracted once more and boot-checked: health OK, status
  honest, frontend HTTP 200, endpoint smoke checks passed.
- Extracted to a **fresh folder**, created a new venv, ran
  `pip install -r requirements.txt -r requirements-tts.txt` (all OK),
  started the server with the exact command start.bat uses
  (`python -m uvicorn backend.main:app --host 127.0.0.1 --port 8766`),
  and ran `tests/smoke_test.py` end-to-end:
  **ALL SMOKE TESTS PASSED** — health, status, template script,
  uploads + thumbnails, project save/reopen, and a full 20 s MP4 render
  (`fall-of-dunkirk_dd48b1.mp4`, stack bottom 400/503 px). Fresh-install
  TTS status: ready, bundled voice found.

## Honest limitations

- **`.bat` files cannot execute on this Linux machine.** install.bat /
  start.bat were written to the PC-package rules (real-Python probe with
  Microsoft Store stub rejection, venv creation, FFmpeg check, browser
  open) but were **not run on Windows**. Everything they invoke was run
  manually here with the identical commands. Windows preflight command
  (`python --version`) is in the README.
- **Ollama mode is code-complete but not live-tested** — no Ollama server
  exists on this machine. The detection + fallback behaviour is tested
  (template mode with an honest note); the Ollama call path follows the
  same JSON contract as the original frontend's OpenAI path.
- **A1111/ComfyUI generation is not live-tested** — neither runs here.
  Detection and the honest 503 are tested; txt2img follows A1111's
  standard `/sdapi/v1/txt2img` API.
- Render jobs are kept in memory; a backend restart forgets a running
  job's status (finished files and export history persist).
- The 63 MB Piper voice ships in the zip but **not** on GitHub (the
  GitHub contents API rejects files that large); the README gives the
  one-link download for repo users.
