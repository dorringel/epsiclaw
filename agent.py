"""
epsiclaw  - the Karpathy treatment for personal AI assistants.

It lives on your phone (Telegram). It knows who you are (MEMORY.md).
It works for you while you sleep (cron). ~500 lines of Python, 6 files.

The same algorithm that runs inside OpenClaw (522K LOC)  - stripped to ε.

What this is NOT:
- Not production software. No auth, no sandboxing, no rate limiting.
- Not a framework. No plugins, no middleware, no config files.
- Not multi-anything. One user, one model, one channel (Telegram).
- Not safe. Tools execute with your permissions. Don't run untrusted prompts.
- Not a vector database. Memory is a markdown file the AI reads and writes.

What this IS:
- A while loop over tool calls, a messaging channel, a cron scheduler,
  and three markdown files. That's the whole claw.
- ~500 lines of Python. 6 files. httpx is the only dependency.

Inspired by Andrej Karpathy's methodology of stripping complex systems
to their algorithmic essence: micrograd, nanoGPT, minbpe, llm.c.
"""

import asyncio
import json
import os
from pathlib import Path

from llm import chat
from tools import TOOL_SCHEMAS, execute_tool, set_current_chat_id
from memory import build_system_prompt, load_session, save_session
from cron import check_due_jobs, mark_job_done
from channel import poll_updates, send_message

DATA_DIR = Path(__file__).parent / "data"


def load_dotenv():
    for p in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip()
            break


def _log(chat_id: str, tag: str, detail: str = ""):
    print(f"[{chat_id}] {tag}{': ' + detail if detail else ''}")


def _tool_summary(name: str, arguments: str) -> str:
    args = json.loads(arguments) if arguments else {}
    parts = [f"{k}={v!r}" for k, v in args.items()]
    return f"{name}({', '.join(parts)})"


async def agent_loop(chat_id: str, user_message: str) -> str:
    """The core claw: ReAct loop over tool calls."""
    set_current_chat_id(chat_id)
    system_prompt = build_system_prompt()
    history = load_session(chat_id)
    history.append({"role": "user", "content": user_message})

    for _ in range(10):
        response = await chat(system_prompt, history, TOOL_SCHEMAS)

        if not response.get("tool_calls"):
            text = response.get("content") or ""
            history.append({"role": "assistant", "content": text})
            save_session(chat_id, history)
            return text

        history.append({
            "role": "assistant",
            "content": response.get("content"),
            "tool_calls": response["tool_calls"],
        })

        for call in response["tool_calls"]:
            _log(chat_id, "tool", _tool_summary(
                call["function"]["name"], call["function"]["arguments"],
            ))
            result = await execute_tool(
                call["function"]["name"],
                call["function"]["arguments"],
            )
            history.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": str(result),
            })

    save_session(chat_id, history)
    return "I've reached my tool-use limit for this turn."


def _allowed_chat_ids() -> set[str] | None:
    raw = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "")
    ids = {x.strip() for x in raw.split(",") if x.strip()}
    return ids or None


async def main():
    load_dotenv()
    DATA_DIR.mkdir(exist_ok=True)
    allowed = _allowed_chat_ids()
    if allowed:
        print(f"epsiclaw is running. Accepting chat IDs: {allowed}")
    else:
        print("epsiclaw is running. Accepting ALL chat IDs (set TELEGRAM_ALLOWED_CHAT_IDS to restrict).")

    last_update_id = 0
    while True:
        due_jobs = check_due_jobs()
        for job in due_jobs:
            _log(job["chat_id"], "cron", job["description"])
            response = await agent_loop(
                job["chat_id"], f"[CRON REMINDER] {job['description']}"
            )
            _log(job["chat_id"], "bot", response[:200])
            await send_message(job["chat_id"], response)
            mark_job_done(job["id"])

        updates, last_update_id = await poll_updates(last_update_id)
        for update in updates:
            msg = update.get("message", {})
            chat_id = str(msg["chat"]["id"])
            if allowed and chat_id not in allowed:
                continue
            text = msg.get("text", "")
            if text:
                _log(chat_id, "user", text)
                try:
                    response = await agent_loop(chat_id, text)
                    _log(chat_id, "bot", response[:200])
                    await send_message(chat_id, response)
                except Exception as e:
                    _log(chat_id, "error", str(e))
                    await send_message(chat_id, f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
