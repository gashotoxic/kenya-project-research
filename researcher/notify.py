"""Telegram digest delivery with message_id capture.

Secrets are env-sourced only (TELEGRAM_BOT_TOKEN), never in code, never in
logs: any error string is redacted before it leaves this module. The chat id
comes from --chat-id, TELEGRAM_CHAT_ID, or TELEGRAM_HOME_CHANNEL
(accepts bare ids and 'telegram:<id>' forms).

The returned message_id is the delivery proof (fleet standard).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API_BASE = "https://api.telegram.org"
RETRIES = 3


def _redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def resolve_chat_id(explicit=None):
    """First usable chat id from CLI arg or env; None when absent."""
    candidates = [
        explicit,
        os.environ.get("TELEGRAM_CHAT_ID"),
        os.environ.get("TELEGRAM_HOME_CHANNEL"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate).strip()
        if value.startswith("telegram:"):
            value = value.split(":", 2)[1]
        if value.lstrip("-").isdigit():
            return value
    return None


def send_digest(text: str, chat_id=None, token=None, timeout: float = 15.0) -> dict:
    """POST the digest. Returns {"ok", "message_id", "chat_id", "error"}."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = resolve_chat_id(chat_id)
    if not token or not chat:
        return {
            "ok": False,
            "message_id": None,
            "chat_id": chat,
            "error": "TELEGRAM_BOT_TOKEN and chat id must come from env/CLI",
        }

    payload = json.dumps({"chat_id": chat, "text": text}).encode("utf-8")
    url = f"{API_BASE}/bot{token}/sendMessage"
    last_error = None
    for attempt in range(RETRIES):
        try:
            request = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            if data.get("ok"):
                return {
                    "ok": True,
                    "message_id": data.get("result", {}).get("message_id"),
                    "chat_id": chat,
                    "error": None,
                }
            last_error = f"api error: {data.get('description')}"
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            last_error = f"HTTP {exc.code}: {body}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(2 ** attempt)
    return {
        "ok": False,
        "message_id": None,
        "chat_id": chat,
        "error": _redact(str(last_error), [token]),
    }
