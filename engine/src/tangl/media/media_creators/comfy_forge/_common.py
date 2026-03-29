from __future__ import annotations

from typing import Any

from tangl.config import settings


def stableforge_config() -> Any | None:
    content = getattr(settings, "content", None)
    apis = getattr(content, "apis", None) if content is not None else None
    stableforge = getattr(apis, "stableforge", None) if apis is not None else None
    if stableforge is not None:
        return stableforge

    media = getattr(settings, "media", None)
    apis = getattr(media, "apis", None) if media is not None else None
    return getattr(apis, "stableforge", None) if apis is not None else None


def configured_comfy_url() -> str | None:
    stableforge = stableforge_config()
    if stableforge is None:
        return None
    workers = getattr(stableforge, "comfy_workers", None) or []
    first = workers[0] if workers else None
    return str(first) if isinstance(first, str) and first else None


def history_error(history: dict[str, Any]) -> str | None:
    status = history.get("status")
    if isinstance(status, dict):
        messages = status.get("messages")
        if isinstance(messages, list):
            for item in messages:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                message_kind = item[0]
                message_payload = item[1]
                if message_kind == "execution_error" and isinstance(message_payload, dict):
                    details = message_payload.get("exception_message") or message_payload.get("error")
                    if isinstance(details, str) and details.strip():
                        return details.strip()
                    return "execution_error"
        status_str = status.get("status_str")
        if isinstance(status_str, str) and status_str.casefold() in {"error", "failed"}:
            return status_str
    return None
