from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator, get_user_locks
from tangl.service import Orchestrator
from tangl.service.response.info_response import UserInfo
from tangl.service.response.info_response.user_info import UserSecret
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret, uuid_for_key


router = APIRouter(tags=["User"])


def _call(orchestrator: Orchestrator, endpoint: str, /, **params: Any) -> Any:
    return orchestrator.execute(endpoint, **params)


@router.get("/info")
async def get_user_info(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None)
) -> UserInfo:
    """Return profile information for the authenticated user."""

    user_id = uuid_for_key(api_key)
    return _call(orchestrator, "UserController.get_user_info", user_id=user_id)


@router.post("/create")
async def create_user(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    secret: str = Query(example=settings.client.secret, default=None),
):
    """Create a user and return the secret metadata for clients."""

    user = _call(orchestrator, "UserController.create_user", secret=secret)
    user_id = getattr(user, "uid", None)
    if user_id is None:
        raise HTTPException(status_code=500, detail="Failed to create user")
    if orchestrator.persistence is not None:
        orchestrator.persistence.save(user)
    api_info = _call(orchestrator, "UserController.get_key_for_secret", secret=secret)
    api_key = getattr(api_info, "api_key", None) or key_for_secret(secret)
    return UserSecret(user_secret=secret, api_key=api_key)


@router.put("/world")
async def set_user_world():
    """Linking users to worlds is not yet implemented in the orchestrated REST API."""

    raise HTTPException(status_code=501, detail="Setting user worlds is not yet supported")


@router.put("/secret")
async def update_user_secret(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_locks = Depends(get_user_locks),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    secret: str = Query(example=settings.client.secret, default=None),
):
    """Update the secret for the authenticated user and surface the new API key."""

    user_id = uuid_for_key(api_key)
    async with user_locks[user_id]:
        info = _call(orchestrator, "UserController.update_user", user_id=user_id, secret=secret)
    api_key_value = getattr(info, "api_key", None)
    secret_value = getattr(info, "secret", secret)
    if api_key_value is None:
        api_key_value = key_for_secret(secret_value)
    return UserSecret(user_secret=secret_value, api_key=api_key_value, user_id=user_id)


@router.delete("/drop")
async def drop_user(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
):
    """Remove the authenticated user and purge persisted resources."""

    user_id = uuid_for_key(api_key)
    identifiers = _call(orchestrator, "UserController.drop_user", user_id=user_id)
    persistence = orchestrator.persistence
    if persistence is not None and isinstance(identifiers, Iterable):
        for identifier in identifiers:
            if not isinstance(identifier, UUID):
                continue
            try:
                persistence.remove(identifier)
            except KeyError:
                continue



