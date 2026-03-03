"""Service38 user controller endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import computed_field

from tangl.service.api_endpoint import HasApiEndpoints
from tangl.service.response.info_response import UserInfo
from tangl.service.user.user import User
from tangl.service38.api_endpoint import (
    AccessLevel,
    ApiEndpoint38,
    MethodType,
    ResourceBinding,
    ResponseType,
)
from tangl.service38.response import InfoModel, RuntimeInfo
from tangl.type_hints import Hash
from tangl.utils.hash_secret import key_for_secret


_TRUE_STRINGS = {"1", "true", "t", "yes", "y", "on"}
_FALSE_STRINGS = {"0", "false", "f", "no", "n", "off", ""}


def _parse_bool_flag(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True
        if normalized in _FALSE_STRINGS:
            return False
    raise ValueError(f"{field_name} must be a boolean-like value")


def _parse_datetime_field(value: Any, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO datetime string") from exc
    raise ValueError(f"{field_name} must be a datetime or ISO datetime string")


class ApiKeyInfo(InfoModel):
    """Encoded API key metadata returned after user updates."""

    secret: str

    @computed_field  # type: ignore[misc]
    @property
    def api_key(self) -> str:
        return key_for_secret(self.secret)


class UserController(HasApiEndpoints):
    """Service38 user controller with explicit v38 semantics."""

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
        response_type=ResponseType.RUNTIME,
        binds=(),
    )
    def create_user(self, **kwargs: Hash) -> RuntimeInfo:
        secret = kwargs.pop("secret", None)
        user = User(**kwargs)
        if isinstance(secret, str) and secret:
            user.set_secret(secret)
        return RuntimeInfo.ok(message="User created", user=user, user_id=str(user.uid))

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.USER,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER,),
    )
    def update_user(self, user: User, **kwargs: Hash) -> RuntimeInfo:
        secret = kwargs.pop("secret", None)
        api_key: str | None = None
        if isinstance(secret, str) and secret:
            user.set_secret(secret)
            api_key = key_for_secret(secret)

        if "last_played_dt" in kwargs:
            user.last_played_dt = _parse_datetime_field(
                kwargs["last_played_dt"],
                field_name="last_played_dt",
            )
        if "privileged" in kwargs:
            user.privileged = _parse_bool_flag(
                kwargs["privileged"],
                field_name="privileged",
            )

        details: dict[str, Any] = {"user_id": str(user.uid)}
        if api_key is not None:
            details["api_key"] = api_key
        return RuntimeInfo.ok(message="User updated", **details)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.USER,
        method_type=MethodType.READ,
        response_type=ResponseType.INFO,
        binds=(ResourceBinding.USER,),
    )
    def get_user_info(self, user: User, **kwargs: Hash) -> UserInfo:
        return UserInfo.from_user(user, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.USER,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER,),
    )
    def drop_user(self, user: User, **kwargs: Hash) -> RuntimeInfo:
        _ = kwargs
        dropped_ledger_id = user.current_ledger_id
        user.current_ledger_id = None
        details: dict[str, Any] = {"user_id": str(user.uid)}
        if dropped_ledger_id is not None:
            details["dropped_ledger_id"] = str(dropped_ledger_id)
        return RuntimeInfo.ok(message="User dropped", **details)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        group="system",
        response_type=ResponseType.INFO,
        binds=(),
    )
    def get_key_for_secret(self, secret: str, **kwargs: Hash) -> ApiKeyInfo:
        _ = kwargs
        return ApiKeyInfo(secret=secret)


__all__ = ["ApiKeyInfo", "UserController"]
