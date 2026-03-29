from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from tangl.config import settings
from tangl.rest.dependencies_gateway import (
    get_service_manager,
    get_user_locks,
    require_service_access,
    resolve_user_auth,
)
from tangl.service import ServiceManager
from tangl.service.exceptions import AccessDeniedError, AuthMismatchError
from tangl.service.response import RuntimeInfo, UserInfo, UserSecret
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret


router = APIRouter(tags=["User"])


def _call_service_method(
    service_manager: ServiceManager,
    method_name: str,
    **params: object,
) -> object:
    method = getattr(service_manager, method_name)
    try:
        return method(**params)
    except (AccessDeniedError, AuthMismatchError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/info")
async def get_user_info(
    service_manager: ServiceManager = Depends(get_service_manager),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> UserInfo:
    """Return profile information for the authenticated user."""

    _ = render_profile
    user_auth = resolve_user_auth(api_key, service_manager=service_manager)
    require_service_access("get_user_info", user_auth=user_auth)
    return _call_service_method(
        service_manager,
        "get_user_info",
        user_id=user_auth.user_id,
        user_auth=user_auth,
    )


@router.post("/create")
async def create_user(
    service_manager: ServiceManager = Depends(get_service_manager),
    secret: str = Query(example=settings.client.secret, default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> UserSecret:
    """Create a user and return the secret metadata for clients."""

    _ = render_profile
    require_service_access("create_user")
    created = service_manager.create_user(secret=secret)
    if not isinstance(created, RuntimeInfo):
        raise HTTPException(status_code=500, detail="Failed to create user")
    if created.status != "ok":
        raise HTTPException(status_code=500, detail=created.message or "Failed to create user")
    return service_manager.get_key_for_secret(secret=secret)


@router.put("/world")
async def set_user_world():
    """Linking users to worlds is not yet implemented in the REST API."""

    raise HTTPException(status_code=501, detail="Setting user worlds is not yet supported")


@router.put("/secret")
async def update_user_secret(
    service_manager: ServiceManager = Depends(get_service_manager),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    secret: str = Query(example=settings.client.secret, default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> UserSecret:
    """Update the secret for the authenticated user and surface the new API key."""

    _ = render_profile
    user_auth = resolve_user_auth(api_key, service_manager=service_manager)
    require_service_access("update_user", user_auth=user_auth)
    async with user_locks[user_auth.user_id]:
        _call_service_method(
            service_manager,
            "update_user",
            user_id=user_auth.user_id,
            user_auth=user_auth,
            secret=secret,
        )
    return UserSecret(
        user_secret=secret,
        api_key=key_for_secret(secret),
        user_id=user_auth.user_id,
    )


@router.delete("/drop")
async def drop_user(
    service_manager: ServiceManager = Depends(get_service_manager),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    render_profile: str = Query(default="raw", description="Response rendering profile."),
) -> RuntimeInfo:
    """Remove the authenticated user and purge persisted resources."""

    _ = render_profile
    user_auth = resolve_user_auth(api_key, service_manager=service_manager)
    require_service_access("drop_user", user_auth=user_auth)
    return _call_service_method(
        service_manager,
        "drop_user",
        user_id=user_auth.user_id,
        user_auth=user_auth,
    )
