from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator
from tangl.service import Orchestrator
from tangl.utils.uuid_for_secret import key_for_secret

from .response_models import UserSecret


router = APIRouter(tags=["System"])


def _call(orchestrator: Orchestrator, endpoint: str, /, **params: Any) -> Any:
    return orchestrator.execute(endpoint, **params)


@router.get("/info")
async def get_system_info(orchestrator: Orchestrator = Depends(get_orchestrator)):
    """Return high-level information about the running service."""

    status = _call(orchestrator, "SystemController.get_system_info")
    if hasattr(status, "guide_url"):
        setattr(status, "guide_url", "/guide")
    elif isinstance(status, dict):
        status.setdefault("guide_url", "/guide")
    return status


@router.get("/worlds")
async def get_worlds(orchestrator: Orchestrator = Depends(get_orchestrator)):
    """List the available worlds registered with the service."""

    return _call(orchestrator, "WorldController.list_worlds")


@router.get("/secret")
async def get_key_for_secret(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    secret: str = Query(example=settings.client.secret, default=None),
):
    """Encode ``secret`` as an API key for clients."""

    info = _call(orchestrator, "UserController.get_key_for_secret", secret=secret)
    api_key = getattr(info, "api_key", None) or key_for_secret(secret)
    secret_value = getattr(info, "secret", secret)
    user_id = getattr(info, "user_id", None)
    return UserSecret(user_secret=secret_value, api_key=api_key, user_id=user_id)
