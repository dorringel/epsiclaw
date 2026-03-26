"""LLM client. One provider, one model, one function."""

import os
import httpx


async def chat(
    system_prompt: str, messages: list, tools: list | None = None
) -> dict:
    """Call the LLM. Returns {"content": str|None, "tool_calls": list|None}."""
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    api_url = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            api_url,
            headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
            json=payload,
        )
        resp.raise_for_status()

    choice = resp.json()["choices"][0]["message"]
    return {
        "content": choice.get("content"),
        "tool_calls": choice.get("tool_calls"),
    }
