"""Cron scheduler. Persisted to data/cron.json."""

import json
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CRON_FILE = DATA_DIR / "cron.json"


def _load() -> list:
    if not CRON_FILE.exists():
        return []
    return json.loads(CRON_FILE.read_text())


def _save(jobs: list):
    DATA_DIR.mkdir(exist_ok=True)
    CRON_FILE.write_text(json.dumps(jobs, indent=2))


def add_job(description: str, datetime_str: str, chat_id: str) -> str:
    jobs = _load()
    job_id = uuid.uuid4().hex[:8]
    jobs.append({
        "id": job_id,
        "description": description,
        "datetime": datetime_str,
        "chat_id": chat_id,
    })
    _save(jobs)
    return job_id


def list_jobs() -> list:
    return _load()


def remove_job(job_id: str) -> bool:
    jobs = _load()
    filtered = [j for j in jobs if j["id"] != job_id]
    _save(filtered)
    return len(filtered) < len(jobs)


def check_due_jobs() -> list:
    now = datetime.now()
    due = []
    for job in _load():
        try:
            job_time = datetime.strptime(job["datetime"], "%Y-%m-%d %H:%M")
            if job_time <= now:
                due.append(job)
        except ValueError:
            continue
    return due


def mark_job_done(job_id: str):
    jobs = _load()
    jobs = [j for j in jobs if j["id"] != job_id]
    _save(jobs)
