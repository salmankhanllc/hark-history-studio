"""In-memory background job registry (render jobs)."""
import threading
import time

_jobs = {}
_lock = threading.Lock()


def create(job_id: str, kind: str) -> dict:
    job = {
        "id": job_id, "kind": kind, "status": "queued", "progress": 0.0,
        "message": "Queued", "error": None, "result": None,
        "created_at": time.time(), "updated_at": time.time(),
    }
    with _lock:
        _jobs[job_id] = job
    return job


def update(job_id: str, **fields) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.update(fields)
            job["updated_at"] = time.time()


def get(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
