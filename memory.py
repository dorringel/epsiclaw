"""Memory system: SOUL.md + USER.md + MEMORY.md + session history."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
MEMORY_FILE = DATA_DIR / "MEMORY.md"

MAX_SESSION_MESSAGES = 50


def _ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)


def _read_md(path: Path) -> str:
    return path.read_text().strip() if path.exists() else ""


def build_system_prompt() -> str:
    """Assemble system prompt from SOUL.md + USER.md + MEMORY.md."""
    soul = _read_md(BASE_DIR / "SOUL.md")
    user = _read_md(BASE_DIR / "USER.md")
    memory = _read_md(MEMORY_FILE)

    parts = []
    if soul:
        parts.append(soul)
    if user:
        parts.append(f"## About the user\n\n{user}")
    if memory:
        parts.append(f"## Your memory\n\n{memory}")
    return "\n\n---\n\n".join(parts) or "You are a helpful personal assistant."


def read_memory() -> str:
    return _read_md(MEMORY_FILE) or "Memory is empty."


def write_memory(content: str):
    _ensure_dirs()
    MEMORY_FILE.write_text(content)


def load_session(chat_id: str) -> list:
    _ensure_dirs()
    path = SESSIONS_DIR / f"{chat_id}.jsonl"
    if not path.exists():
        return []
    messages = []
    for line in path.read_text().splitlines():
        if line.strip():
            messages.append(json.loads(line))
    return messages[-MAX_SESSION_MESSAGES:]


def save_session(chat_id: str, messages: list):
    _ensure_dirs()
    path = SESSIONS_DIR / f"{chat_id}.jsonl"
    with open(path, "w") as f:
        for msg in messages[-MAX_SESSION_MESSAGES:]:
            f.write(json.dumps(msg) + "\n")
