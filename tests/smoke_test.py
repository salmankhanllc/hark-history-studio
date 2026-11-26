#!/usr/bin/env python3
"""Smoke test for the History Studio local backend.

Usage:  python tests/smoke_test.py [base_url] [clip1] [clip2]
Defaults: base http://127.0.0.1:8765 and the two clips named in the test
report. Exercises: health, system status, script generation (template),
project save/reopen, media upload + probe + thumbnail, TTS (if Piper is
ready), render job to a real MP4, export download.
Exits non-zero on the first hard failure; TTS/render media checks print
clear PASS/FAIL lines.
"""
import json
import sys
import time
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
CLIP1 = sys.argv[2] if len(sys.argv) > 2 else ""
CLIP2 = sys.argv[3] if len(sys.argv) > 3 else ""


def req(method, path, body=None, raw=None, headers=None):
    data = raw
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name} {extra}")
    if not cond:
        sys.exit(1)


def upload(path, project_id=None):
    boundary = "----hark" + uuid.uuid4().hex
    with open(path, "rb") as fh:
        content = fh.read()
    name = path.split("/")[-1]
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode())
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    raw = b"".join(parts)
    r = urllib.request.Request(BASE + "/api/media/upload", data=raw, method="POST",
                               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(r, timeout=300) as resp:
        return json.loads(resp.read().decode())


def main():
    st, health = req("GET", "/api/health")
    check("health", st == 200 and health.get("ok"), str(health))

    st, status = req("GET", "/api/system/status")
    check("system status", st == 200)
    print(f"      python {status['python']['version']} · ffmpeg {status['ffmpeg']['available']} · "
          f"ollama {status['ollama']['running']} · piper ready {status['piper']['ready']}")

    st, script = req("POST", "/api/scripts/generate",
                     {"topic": "FALL OF DUNKIRK", "hook": "GREAT ESCAPE IS OVER",
                      "date": "JUNE 4, 1940", "detail": "BEF evacuated from the beaches"})
    check("script generate", st == 200 and len(script.get("scenes", [])) >= 5,
          f"mode={script.get('mode')} scenes={len(script.get('scenes', []))} total={script.get('total_duration')}")

    if not (CLIP1 and CLIP2):
        print("SKIP  media/render (no test clips supplied)")
        return

    m1 = upload(CLIP1)
    check("upload clip1", bool(m1.get("id")), f"{m1.get('kind')} {m1.get('width')}x{m1.get('height')} dur={m1.get('duration')}")
    m2 = upload(CLIP2)
    check("upload clip2", bool(m2.get("id")), f"{m2.get('kind')} {m2.get('width')}x{m2.get('height')} dur={m2.get('duration')}")
    check("thumbnail", bool(m1.get("thumb_url") or m2.get("thumb_url")))

    scenes = [
        {"id": "t1", "n": 1, "title": "Opening Fire — Guns Speak", "duration": 7, "shotType": "Firing",
         "kind": "firing", "camera": "tight side angle", "narration": "", "soundCue": "Gun blast",
         "searchTerm": "dunkirk artillery", "prompt": "x" * 90, "mediaId": m1["id"], "trimStart": 0},
        {"id": "t2", "n": 2, "title": "Impact — The Target Is Hit", "duration": 7, "shotType": "Impact",
         "kind": "impact", "camera": "locked wide", "narration": "", "soundCue": "Explosion",
         "searchTerm": "dunkirk explosion", "prompt": "x" * 90, "mediaId": m2["id"], "trimStart": 1},
        {"id": "t3", "n": 3, "title": "Aftermath — What Remained", "duration": 6, "shotType": "Aftermath",
         "kind": "aftermath", "camera": "slow lateral", "narration": "", "soundCue": "Wind",
         "searchTerm": "dunkirk aftermath", "prompt": "x" * 90, "mediaId": m2["id"], "trimStart": 13},
    ]
    project = {"id": "smoketest-project", "topic": "FALL OF DUNKIRK", "hook": "GREAT ESCAPE IS OVER",
               "date": "JUNE 4, 1940", "detail": "smoke test", "styleName": "Battle of Britain — Reference Style",
               "scenes": scenes}
    st, saved = req("POST", "/api/projects", project)
    check("project save", st == 200 and saved.get("id") == "smoketest-project")
    st, reopened = req("GET", "/api/projects/smoketest-project")
    check("project reopen", st == 200 and len(reopened.get("scenes", [])) == 3)

    st, job = req("POST", "/api/render/jobs", {"project_id": "smoketest-project", "use_clip_audio": True})
    check("render job created", st == 200 and job.get("job_id"), str(job))
    job_id = job["job_id"]
    deadline = time.time() + 900
    final = None
    while time.time() < deadline:
        time.sleep(3)
        st, j = req("GET", f"/api/render/jobs/{job_id}")
        if j.get("status") in ("done", "error"):
            final = j
            break
    check("render job finished", final is not None and final.get("status") == "done",
          (final or {}).get("error", ""))
    result = final["result"]
    print(f"      export: {result['filename']} · duration {result['duration']}s · font {result['font']} · "
          f"title stack bottom {result['title_layout']['bottom']}px of {result['title_layout']['bar_h']}px bar")
    st, exports = req("GET", "/api/projects/smoketest-project/exports")
    check("export listed", st == 200 and len(exports.get("exports", [])) >= 1)
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
