"""SQLite storage (stdlib sqlite3 only).

Stores full project JSON plus normalised scene / media / export rows so
projects can be reopened exactly as they were left.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

from . import config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  topic TEXT NOT NULL DEFAULT '',
  hook TEXT DEFAULT '',
  date_line TEXT DEFAULT '',
  detail TEXT DEFAULT '',
  style_name TEXT DEFAULT '',
  project_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenes (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  n INTEGER NOT NULL,
  title TEXT DEFAULT '',
  duration REAL DEFAULT 0,
  shot_type TEXT DEFAULT '',
  kind TEXT DEFAULT '',
  camera TEXT DEFAULT '',
  narration TEXT DEFAULT '',
  sound_cue TEXT DEFAULT '',
  search_term TEXT DEFAULT '',
  prompt TEXT DEFAULT '',
  media_id TEXT,
  scene_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  scene_id TEXT,
  original_name TEXT NOT NULL,
  stored_name TEXT NOT NULL,
  rel_path TEXT NOT NULL,
  kind TEXT NOT NULL,
  size_bytes INTEGER DEFAULT 0,
  duration REAL,
  width INTEGER,
  height INTEGER,
  tags TEXT DEFAULT '',
  description TEXT DEFAULT '',
  source_info TEXT DEFAULT '',
  thumb_rel_path TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exports (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  filename TEXT NOT NULL,
  rel_path TEXT NOT NULL,
  settings_json TEXT DEFAULT '{}',
  status TEXT DEFAULT 'done',
  created_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _lock, connect() as conn:
        conn.executescript(SCHEMA)


# ---------------- projects ----------------

def upsert_project(project: dict) -> dict:
    pid = project["id"]
    created = project.get("createdAt") or now_iso()
    updated = now_iso()
    with _lock, connect() as conn:
        existing = conn.execute("SELECT created_at FROM projects WHERE id = ?", (pid,)).fetchone()
        if existing:
            created = existing["created_at"]
        conn.execute(
            """INSERT INTO projects (id, topic, hook, date_line, detail, style_name, project_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET topic=excluded.topic, hook=excluded.hook,
                 date_line=excluded.date_line, detail=excluded.detail, style_name=excluded.style_name,
                 project_json=excluded.project_json, updated_at=excluded.updated_at""",
            (pid, project.get("topic", ""), project.get("hook", ""), project.get("date", ""),
             project.get("detail", ""), project.get("styleName", ""),
             json.dumps(project), created, updated),
        )
        conn.execute("DELETE FROM scenes WHERE project_id = ?", (pid,))
        for sc in project.get("scenes", []):
            conn.execute(
                """INSERT INTO scenes (id, project_id, n, title, duration, shot_type, kind, camera,
                     narration, sound_cue, search_term, prompt, media_id, scene_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sc.get("id") or f"{pid}-s{sc.get('n', 0)}", pid, sc.get("n", 0), sc.get("title", ""),
                 sc.get("duration", 0), sc.get("shotType", ""), sc.get("kind", ""), sc.get("camera", ""),
                 sc.get("narration", ""), sc.get("soundCue", ""), sc.get("searchTerm", ""),
                 sc.get("prompt", ""), sc.get("mediaId"), json.dumps(sc)),
            )
    return get_project(pid)


def get_project(pid: str):
    with connect() as conn:
        row = conn.execute("SELECT project_json FROM projects WHERE id = ?", (pid,)).fetchone()
    if not row:
        return None
    return json.loads(row["project_json"])


def list_projects() -> list:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, topic, hook, date_line, style_name, created_at, updated_at, project_json "
            "FROM projects ORDER BY updated_at DESC").fetchall()
    out = []
    for r in rows:
        try:
            scenes = json.loads(r["project_json"]).get("scenes", [])
        except Exception:
            scenes = []
        out.append({
            "id": r["id"], "topic": r["topic"], "hook": r["hook"], "date": r["date_line"],
            "styleName": r["style_name"], "sceneCount": len(scenes),
            "totalDuration": sum(float(s.get("duration") or 0) for s in scenes),
            "createdAt": r["created_at"], "updatedAt": r["updated_at"],
        })
    return out


def delete_project(pid: str) -> bool:
    with _lock, connect() as conn:
        conn.execute("DELETE FROM scenes WHERE project_id = ?", (pid,))
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
        return cur.rowcount > 0


# ---------------- media ----------------

def insert_media(row: dict) -> dict:
    with _lock, connect() as conn:
        conn.execute(
            """INSERT INTO media (id, project_id, scene_id, original_name, stored_name, rel_path, kind,
                 size_bytes, duration, width, height, tags, description, source_info, thumb_rel_path, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (row["id"], row.get("project_id"), row.get("scene_id"), row["original_name"],
             row["stored_name"], row["rel_path"], row["kind"], row.get("size_bytes", 0),
             row.get("duration"), row.get("width"), row.get("height"), row.get("tags", ""),
             row.get("description", ""), row.get("source_info", ""), row.get("thumb_rel_path"),
             row.get("created_at") or now_iso()),
        )
    return get_media(row["id"])


def get_media(mid: str):
    with connect() as conn:
        row = conn.execute("SELECT * FROM media WHERE id = ?", (mid,)).fetchone()
    return dict(row) if row else None


def list_media(project_id: str = None) -> list:
    with connect() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM media WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM media ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_media(mid: str, fields: dict):
    allowed = {"tags", "description", "source_info", "scene_id", "project_id"}
    sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not sets:
        return get_media(mid)
    clause = ", ".join(f"{k} = ?" for k in sets)
    with _lock, connect() as conn:
        conn.execute(f"UPDATE media SET {clause} WHERE id = ?", (*sets.values(), mid))
    return get_media(mid)


def delete_media(mid: str) -> bool:
    with _lock, connect() as conn:
        cur = conn.execute("DELETE FROM media WHERE id = ?", (mid,))
        return cur.rowcount > 0


# ---------------- exports ----------------

def insert_export(row: dict) -> dict:
    with _lock, connect() as conn:
        conn.execute(
            "INSERT INTO exports (id, project_id, filename, rel_path, settings_json, status, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (row["id"], row.get("project_id"), row["filename"], row["rel_path"],
             json.dumps(row.get("settings", {})), row.get("status", "done"), now_iso()),
        )
    return get_export(row["id"])


def get_export(eid: str):
    with connect() as conn:
        row = conn.execute("SELECT * FROM exports WHERE id = ?", (eid,)).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["settings"] = json.loads(d.pop("settings_json") or "{}")
    except Exception:
        d["settings"] = {}
    return d


def list_exports(project_id: str = None) -> list:
    with connect() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM exports WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM exports ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["settings"] = json.loads(d.pop("settings_json") or "{}")
        except Exception:
            d["settings"] = {}
        out.append(d)
    return out
