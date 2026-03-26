"""Tool registry and built-in tools."""

import json
import os
from datetime import datetime

import httpx

TOOL_REGISTRY: dict[str, callable] = {}
TOOL_SCHEMAS: list[dict] = []

_current_chat_id: str | None = None


def set_current_chat_id(chat_id: str):
    global _current_chat_id
    _current_chat_id = chat_id


def tool(name: str, description: str, parameters: dict):
    """Register a tool with its OpenAI function-calling schema."""
    def decorator(fn):
        TOOL_REGISTRY[name] = fn
        TOOL_SCHEMAS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })
        return fn
    return decorator


async def execute_tool(name: str, arguments: str) -> str:
    """Dispatch a tool call by name."""
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    try:
        args = json.loads(arguments) if arguments else {}
        result = fn(**args)
        if hasattr(result, "__await__"):
            result = await result
        return str(result)
    except Exception as e:
        return f"Tool error: {e}"


# --- Built-in tools ---


@tool("get_current_time", "Get the current date and time.", {
    "type": "object", "properties": {},
})
def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")


@tool("web_search", "Search the web for current information.", {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"},
    },
    "required": ["query"],
})
async def web_search(query: str) -> str:
    api_key = os.environ.get("WEB_SEARCH_API_KEY", "")
    if not api_key:
        return "Web search not configured (missing WEB_SEARCH_API_KEY)."
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={"query": query, "api_key": api_key, "max_results": 3},
        )
        resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return "No results found."
    return "\n\n".join(
        f"**{r['title']}**\n{r['url']}\n{r.get('content', '')[:300]}"
        for r in results
    )


@tool("memory_read", "Read your long-term memory about the user.", {
    "type": "object", "properties": {},
})
def memory_read() -> str:
    from memory import read_memory
    return read_memory()


@tool("memory_write", "Overwrite your long-term memory. Use to remember important "
     "facts about the user across conversations.", {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "Full updated memory content (markdown)",
        },
    },
    "required": ["content"],
})
def memory_write(content: str) -> str:
    from memory import write_memory
    write_memory(content)
    return "Memory updated."


@tool("cron_add", "Schedule a one-time reminder. The bot will message the user "
     "at the specified time.", {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "What to remind about",
        },
        "datetime_str": {
            "type": "string",
            "description": "When to fire, format: YYYY-MM-DD HH:MM",
        },
    },
    "required": ["description", "datetime_str"],
})
def cron_add(description: str, datetime_str: str) -> str:
    from cron import add_job
    job_id = add_job(description, datetime_str, _current_chat_id)
    return f"Scheduled: '{description}' at {datetime_str} (id: {job_id})"


@tool("cron_list", "List all scheduled reminders.", {
    "type": "object", "properties": {},
})
def cron_list() -> str:
    from cron import list_jobs
    jobs = list_jobs()
    if not jobs:
        return "No scheduled jobs."
    return "\n".join(
        f"- [{j['id']}] {j['datetime']}  - {j['description']}" for j in jobs
    )


@tool("cron_remove", "Remove a scheduled reminder by ID.", {
    "type": "object",
    "properties": {
        "job_id": {"type": "string", "description": "Job ID to remove"},
    },
    "required": ["job_id"],
})
def cron_remove(job_id: str) -> str:
    from cron import remove_job
    return f"Removed job {job_id}." if remove_job(job_id) else f"Job {job_id} not found."
