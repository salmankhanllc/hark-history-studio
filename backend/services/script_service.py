"""Local script generation.

Two honest modes:
- "template": the deterministic studio engine (a port of the frontend demo
  engine) — always works offline, no model needed.
- "ollama": used only when a local Ollama server is actually running AND has
  at least one model installed. Any failure falls back to the template
  engine and the response says so. Nothing is faked.
"""
import json
import logging
import urllib.request
import urllib.error

from .. import config
from .scene_service import build_prompt, normalize_scenes

log = logging.getLogger("hark.script")

BOB_STYLE = {
    "name": "Battle of Britain — Reference Style",
    "era": "Summer 1940, RAF Fighter Command, south-east England",
    "subject": "Period-correct British aircraft, airfields and personnel only — Hurricanes, Spitfires, RAF flying kit",
    "look": "Cinematic period realism shot on virtual 35mm: visible film grain, soft halation on highlights, dust and exhaust haze in the air",
    "colour": "Muted period colour — khaki, slate grey, dull brass, faded sky blue, chalk white — slightly desaturated, warm shadows, no HDR pop",
    "grade": "CLEAR-WHITE grade: bright, clean highlights, lifted whites (gamma ~1.16), never dark or crushed",
    "format": "Vertical 9:16, 1080×1920, action framing, camera at human height",
    "rules": "No drones or aerial establishing shots unless the scene demands it; no modern objects, clothing, signage or aircraft marks; no on-screen text; nothing clean, digital or modern",
}


def style_block(style: dict = None) -> dict:
    s = style or BOB_STYLE
    return {"era": s.get("era", ""), "look": s.get("look", ""), "colour": s.get("colour", ""),
            "grade": s.get("grade", ""), "rules": s.get("rules", "")}


def template_scenes(topic: str, hook: str, date: str, detail: str, style: dict = None) -> list:
    """Deterministic port of the frontend demo engine: 6 scenes,
    firing → impact pairs, aftermath last."""
    T = (topic or "UNTITLED BATTLE")
    D = f" Story detail given: {detail}" if detail else ""
    st = style_block(style)
    raw = [
        {"key": "establish", "title": "The Calm Before — Forces Gather", "dur": 4, "shot": "Establishing", "kind": "scene",
         "subject": "Period troops and equipment in position, waiting",
         "action": "men scan the sky and horizon, engines idle, tension rising",
         "environment": "the battle location at first light",
         "period": "authentic period uniforms, vehicles and markings throughout",
         "lighting": "low early light through haze", "camera": "slow push-in at human height, locked-off feel",
         "narr": f"Narration (if used): “{T.lower()} — it began here.” Combat sound only in the final reel.",
         "sound": "Distant engines, wind, faint radio chatter", "search": f"{T} troops waiting footage"},
        {"key": "firing1", "title": "Opening Fire — Guns Speak", "dur": 4, "shot": "Firing", "kind": "firing",
         "subject": "A period artillery gun / heavy weapon crew in action",
         "action": "the gun FIRES with full recoil and muzzle flash, crew reloading at speed",
         "environment": "gun position, dust and cordite smoke in the air",
         "period": "correct period gun, uniforms and ammunition handling",
         "lighting": "hard daylight, flash lighting the smoke", "camera": "tight side angle, slight shake on the shot",
         "narr": "No narration — the gun is the voice of this scene.",
         "sound": "The gun's own blast, exactly on the firing frame, then recoil and reload clatter",
         "search": f"{T} artillery firing footage"},
        {"key": "impact1", "title": "Impact — The Target Is Hit", "dur": 4, "shot": "Impact", "kind": "impact",
         "subject": "The target position struck by the shells just fired",
         "action": "a direct hit — explosion, debris and dust thrown high, position destroyed",
         "environment": "the receiving end of the fire, immediately after the firing scene",
         "period": "period structures and vehicles, no modern damage effects",
         "lighting": "blast light then thick dust haze", "camera": "locked wide shot so the full destruction reads",
         "narr": "No narration — impact sound carries it.",
         "sound": "Shell arrival whistle cutting straight into the explosion, debris falling",
         "search": f"{T} explosion impact destruction footage"},
        {"key": "firing2", "title": "Second Salvo — Armour Fires", "dur": 4, "shot": "Firing", "kind": "firing",
         "subject": "A period tank / armoured vehicle main gun",
         "action": "the tank FIRES, muzzle blast kicking up dust, hull rocking with recoil",
         "environment": "armour advancing or hull-down in the battle area",
         "period": "period-correct tank model, markings and crew kit",
         "lighting": "bright daylight, blast dust lit by sun", "camera": "low front three-quarter angle, dust washing over lens",
         "narr": "No narration — engine and gun only.",
         "sound": "Main gun blast synced to the flash, engine roar underneath",
         "search": f"{T} tank firing footage"},
        {"key": "impact2", "title": "Impact — Position Destroyed", "dur": 5, "shot": "Impact", "kind": "impact",
         "subject": "A building / strongpoint hit by the tank's fire",
         "action": "the structure is struck and collapses in dust and flame, the biggest destruction of the reel",
         "environment": "the strongpoint at the moment of the hit",
         "period": "period architecture and rubble, no modern materials",
         "lighting": "firelight inside dust cloud", "camera": "steady wide shot, hold on the collapse",
         "narr": "No narration — the collapse is the payoff.",
         "sound": "Impact crack then the long rumble of the collapse",
         "search": f"{T} building destroyed shelling footage"},
        {"key": "aftermath", "title": "Aftermath — What Remained", "dur": 4, "shot": "Aftermath", "kind": "aftermath",
         "subject": "The battlefield after the fighting — wreckage and silence",
         "action": "smoke drifts over wrecks and rubble, a lone figure walks through frame",
         "environment": "the same location, stilled",
         "period": "abandoned period vehicles and equipment, smoke-blackened",
         "lighting": "pale light through smoke", "camera": "very slow lateral move, elegiac and still",
         "narr": f"Closing line (if used): “{hook or 'And then — silence'}.”",
         "sound": "Wind, distant fire crackle, a single far-off engine fading",
         "search": f"{T} aftermath wreckage footage"},
    ]
    scenes = []
    for i, r in enumerate(raw):
        core = {"subject": r["subject"], "action": r["action"],
                "environment": f"{r['environment']}. {st['era']}{D}", "period": r["period"],
                "lighting": r["lighting"], "camera": r["camera"]}
        scenes.append({
            "id": f"tpl-{i + 1}", "n": i + 1, "title": r["title"], "duration": r["dur"],
            "shotType": r["shot"], "kind": r["kind"], "camera": r["camera"],
            "narration": r["narr"], "soundCue": r["sound"], "searchTerm": r["search"],
            "prompt": build_prompt(core, st), "mediaId": None, "trimStart": 0,
        })
    return scenes


# ---------------- Ollama (optional local LLM) ----------------

def ollama_status(timeout: float = 1.5) -> dict:
    try:
        req = urllib.request.Request(config.OLLAMA_URL + "/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        return {"running": True, "models": models, "url": config.OLLAMA_URL}
    except Exception:
        return {"running": False, "models": [], "url": config.OLLAMA_URL}


def _ollama_scenes(topic, hook, date, detail, style, model: str) -> list:
    st = style_block(style)
    sys_prompt = (
        "You are a history short-form video director. Return ONLY JSON: "
        '{"scenes":[{title,duration,shotType,kind,camera,narration,soundCue,searchTerm,subject,action,environment,period,lighting}]} '
        "with 5-7 scenes. kind is one of firing, impact, aftermath, scene. Every firing scene must be "
        "immediately followed by an impact scene; the last scene must be aftermath. Durations 3-6 seconds, "
        "total 15-30. Combat sound cues only, no music."
    )
    usr = (f"Topic (title L1): {topic}\nHook (L2): {hook}\nDate (L3): {date}\n"
           f"Detail: {detail or ''}\nStyle era: {st['era']}")
    body = json.dumps({
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "system", "content": sys_prompt},
                     {"role": "user", "content": usr}],
    }).encode("utf-8")
    req = urllib.request.Request(config.OLLAMA_URL + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parsed = json.loads(data["message"]["content"])
    if not parsed.get("scenes"):
        raise ValueError("Ollama returned no scenes")
    return normalize_scenes(parsed["scenes"], topic, st)


def generate(topic: str, hook: str = "", date: str = "", detail: str = "",
             style: dict = None) -> dict:
    """Returns {mode, note, model, scenes, total_duration}."""
    status = ollama_status()
    if status["running"] and status["models"]:
        model = status["models"][0]
        try:
            scenes = _ollama_scenes(topic, hook, date, detail, style, model)
            return {"mode": "ollama", "model": model,
                    "note": f"Scenes written by your local Ollama model '{model}'. No cloud service was used.",
                    "scenes": scenes,
                    "total_duration": sum(s["duration"] for s in scenes)}
        except Exception as e:
            log.warning("Ollama generation failed, falling back to template: %s", e)
            scenes = template_scenes(topic, hook, date, detail, style)
            return {"mode": "template", "model": None,
                    "note": f"Ollama model '{model}' failed ({e}); the offline template engine wrote these scenes instead.",
                    "scenes": scenes,
                    "total_duration": sum(s["duration"] for s in scenes)}
    scenes = template_scenes(topic, hook, date, detail, style)
    note = ("Offline template engine — no local Ollama model detected. "
            "Install Ollama and pull a model (e.g. 'ollama pull llama3.1') to have scenes written by a local AI.")
    return {"mode": "template", "model": None, "note": note,
            "scenes": scenes, "total_duration": sum(s["duration"] for s in scenes)}
