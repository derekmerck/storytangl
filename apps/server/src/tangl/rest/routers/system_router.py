from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator
from tangl.service import Orchestrator
from tangl.service.response.info_response.user_info import UserSecret
from tangl.service.response.info_response import SystemInfo
from tangl.utils.hash_secret import key_for_secret


router = APIRouter(tags=["System"])


def _call(orchestrator: Orchestrator, endpoint: str, /, **params: Any) -> Any:
    return orchestrator.execute(endpoint, **params)


def _serialize(value: Any) -> Any:
    """Convert native responses into JSON-friendly payloads."""

    from uuid import UUID

    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, set):
        return sorted((_serialize(item) for item in value), key=str)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        try:
            return _serialize(value.model_dump(mode="python"))
        except TypeError:
            return repr(value)
    return value


@router.get("/info")
async def get_system_info(orchestrator: Orchestrator = Depends(get_orchestrator)) -> SystemInfo:
    """Return high-level information about the running service."""

    status = _call(orchestrator, "SystemController.get_system_info")
    if hasattr(status, "guide_url"):
        setattr(status, "guide_url", "/guide")
    elif isinstance(status, dict):
        status.setdefault("guide_url", "/guide")
    return _serialize(status)


@router.get("/worlds")
async def get_worlds(
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> list[dict[str, object]]:
    """List the available worlds registered with the service."""

    return _serialize(_call(orchestrator, "WorldController.list_worlds"))


@router.get("/secret")
async def get_key_for_secret(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    secret: str = Query(example=settings.client.secret, default=None),
) -> UserSecret:
    """Encode ``secret`` as an API key for clients."""

    info = _call(orchestrator, "UserController.get_key_for_secret", secret=secret)
    api_key = getattr(info, "api_key", None) or key_for_secret(secret)
    secret_value = getattr(info, "secret", secret)
    # user_id = getattr(info, "user_id", None)
    return UserSecret(user_secret=secret_value, api_key=api_key)
