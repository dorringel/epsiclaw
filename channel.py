"""Telegram channel. Long polling + send."""

import os
import httpx

POLL_TIMEOUT = 2


def _url(method: str) -> str:
    base = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org/bot")
    return f"{base}{os.environ['TELEGRAM_BOT_TOKEN']}/{method}"


async def poll_updates(last_update_id: int) -> tuple[list, int]:
    """Long-poll for new messages. Returns (updates, new_last_update_id)."""
    async with httpx.AsyncClient(timeout=POLL_TIMEOUT + 5) as client:
        try:
            resp = await client.get(
                _url("getUpdates"),
                params={
                    "offset": last_update_id + 1,
                    "timeout": POLL_TIMEOUT,
                    "allowed_updates": '["message"]',
                },
            )
            resp.raise_for_status()
        except httpx.TimeoutException:
            return [], last_update_id
        except httpx.HTTPError as e:
            print(f"Poll error: {e}")
            return [], last_update_id

    updates = resp.json().get("result", [])
    valid = [
        u for u in updates
        if "message" in u and "text" in u.get("message", {})
    ]
    if updates:
        last_update_id = max(u["update_id"] for u in updates)
    return valid, last_update_id


async def send_message(chat_id: str, text: str):
    """Send a text message. Splits at Telegram's 4096-char limit."""
    if not text:
        return
    chunks = [text[i : i + 4096] for i in range(0, len(text), 4096)]
    async with httpx.AsyncClient(timeout=10) as client:
        for chunk in chunks:
            await client.post(
                _url("sendMessage"),
                json={"chat_id": chat_id, "text": chunk},
            )
