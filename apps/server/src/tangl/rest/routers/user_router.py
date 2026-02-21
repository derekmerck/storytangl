from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from tangl.config import settings
from tangl.rest.dependencies38 import get_service_adapter38, get_user_locks38
from tangl.service.response.info_response import UserInfo
from tangl.service.response.info_response.user_info import UserSecret
from tangl.service38 import GatewayRestAdapter38, ServiceOperation38
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret


router = APIRouter(tags=["User"])


def _call(
    adapter: GatewayRestAdapter38,
    operation: ServiceOperation38,
    /,
    *,
    user_id: UUID | None = None,
    render_profile: str = "raw",
    **params: Any,
) -> Any:
    return adapter.execute_operation(
        operation,
        user_id=user_id,
        render_profile=render_profile,
        **params,
    )


@router.get("/info")
async def get_user_info(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> UserInfo:
    """Return profile information for the authenticated user."""

    user_id = adapter.resolve_user_id(api_key)
    return _call(
        adapter,
        ServiceOperation38.USER_INFO,
        user_id=user_id,
        render_profile=render_profile,
    )


@router.post("/create")
async def create_user(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    secret: str = Query(example=settings.client.secret, default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Create a user and return the secret metadata for clients."""

    user = _call(
        adapter,
        ServiceOperation38.USER_CREATE,
        render_profile=render_profile,
        secret=secret,
    )
    user_id = getattr(user, "uid", None)
    if user_id is None:
        details = getattr(user, "details", None) or {}
        raw_user_id = details.get("user_id") if isinstance(details, dict) else None
        if raw_user_id is not None:
            user_id = UUID(str(raw_user_id))
    if user_id is None:
        raise HTTPException(status_code=500, detail="Failed to create user")
    api_info = _call(
        adapter,
        ServiceOperation38.USER_KEY,
        render_profile=render_profile,
        secret=secret,
    )
    api_key = getattr(api_info, "api_key", None) or key_for_secret(secret)
    return UserSecret(user_secret=secret, api_key=api_key)


@router.put("/world")
async def set_user_world():
    """Linking users to worlds is not yet implemented in the orchestrated REST API."""

    raise HTTPException(status_code=501, detail="Setting user worlds is not yet supported")


@router.put("/secret")
async def update_user_secret(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    user_locks = Depends(get_user_locks38),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    secret: str = Query(example=settings.client.secret, default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Update the secret for the authenticated user and surface the new API key."""

    user_id = adapter.resolve_user_id(api_key)
    async with user_locks[user_id]:
        info = _call(
            adapter,
            ServiceOperation38.USER_UPDATE,
            user_id=user_id,
            render_profile=render_profile,
            secret=secret,
        )
    api_key_value = getattr(info, "api_key", None)
    secret_value = getattr(info, "secret", secret)
    if api_key_value is None:
        api_key_value = key_for_secret(secret_value)
    return UserSecret(user_secret=secret_value, api_key=api_key_value, user_id=user_id)


@router.delete("/drop")
async def drop_user(
    adapter: GatewayRestAdapter38 = Depends(get_service_adapter38),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
):
    """Remove the authenticated user and purge persisted resources."""

    user_id = adapter.resolve_user_id(api_key)
    identifiers = _call(
        adapter,
        ServiceOperation38.USER_DROP,
        user_id=user_id,
        render_profile=render_profile,
    )
    persistence = adapter.persistence
    if persistence is not None and isinstance(identifiers, Iterable):
        for identifier in identifiers:
            if not isinstance(identifier, UUID):
                continue
            try:
                persistence.remove(identifier)
            except KeyError:
                continue
