# Hark History Studio — Portable Edition

A single-file, client-side-only studio for making style-locked history short videos (9:16).

**Just open `index.html` in any browser — no server, no build step.**

## What it does

- **Setup** — OpenAI + Fal.ai API keys saved in the browser (localStorage, masked, clearable). "Load Battle of Britain Template" loads the locked reference style (1940 RAF, film grain, muted period colour, 9:16).
- **Create** — Topic (title L1), Hook (L2), Date (L3); Quality Presets: Professional (Fal Kling 2.5 Turbo Pro) / Standard (Fal Hailuo-02) / Free (SANA-Video 2.0, no key). Generates a style-locked scene breakdown (built-in demo engine, or live GPT-4o from the browser when an OpenAI key is saved, with graceful fallback). Firing scenes are immediately followed by impact scenes; aftermath last.
- **Per scene** — full 8-part video prompt, narration note, combat sound cue, 9 free archive source links (Internet Archive, Wikimedia Commons, PICRYL, NARA, DVIDS, Prelinger, IWM, Europeana, British Pathé), the 8-step quality-enhance recipe, and a Generate Video button.
- **Video generation runs entirely in the browser** — free SANA-Video via its public Gradio API, or Fal.ai via its queue API with your own key. Live status, inline player, download link, plain error messages. Never a fake video.
- **Reel Preview** — 1080×1920-proportioned frame, thick black bars, titles only in the top bar (L1 white 0s, L2 gold ~7s, L3 typewriter ~15.5s), plus a pre-export Quality Checklist.
- **Library** — projects saved in localStorage; open / delete.
- **Production Sheet** — downloadable professional call-sheet (HTML) with titles + timings, per-scene prompts, source links, recipe and status.

## Notes

- Keys and projects never leave the device except to the provider you call (OpenAI / Fal.ai / the SANA demo).
- AI-generated clips are labelled as generated; archive clips are real historical footage.
- To publish on GitHub Pages: push this repo and enable Pages on the main branch — `index.html` is the whole app.
