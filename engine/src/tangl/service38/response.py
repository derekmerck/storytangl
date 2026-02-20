"""Service38-native response primitives."""

from __future__ import annotations

from typing import Any, Literal, Mapping, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from tangl.core import BaseFragment
from tangl.journal.media import MediaFragment


class InfoModel(BaseModel):
    """Marker base for service38 information payloads."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RuntimeInfo(InfoModel):
    """Service38 runtime acknowledgement payload."""

    status: Literal["ok", "error"]
    code: str | None = None
    message: str | None = None
    cursor_id: UUID | None = None
    step: int | None = None
    details: Mapping[str, Any] | None = None

    @classmethod
    def ok(
        cls,
        *,
        cursor_id: UUID | None = None,
        step: int | None = None,
        message: str | None = None,
        **details: Any,
    ) -> "RuntimeInfo":
        return cls(
            status="ok",
            code=None,
            message=message,
            cursor_id=cursor_id,
            step=step,
            details=details or None,
        )

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        *,
        cursor_id: UUID | None = None,
        step: int | None = None,
        **details: Any,
    ) -> "RuntimeInfo":
        return cls(
            status="error",
            code=code,
            message=message,
            cursor_id=cursor_id,
            step=step,
            details=details or None,
        )


def coerce_runtime_info(value: Any) -> RuntimeInfo | None:
    """Best-effort coercion from runtime-like payloads to ``RuntimeInfo``."""

    if isinstance(value, RuntimeInfo):
        return value

    payload: dict[str, Any] | None = None
    if isinstance(value, Mapping):
        payload = dict(value)
    elif isinstance(value, BaseModel):
        payload = value.model_dump(mode="python")
    elif hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        payload = value.model_dump(mode="python")

    if payload is None or "status" not in payload:
        return None

    try:
        return RuntimeInfo.model_validate(payload)
    except ValidationError:
        return None


FragmentStream: TypeAlias = list[BaseFragment]
MediaNative: TypeAlias = MediaFragment
NativeResponse: TypeAlias = FragmentStream | InfoModel | RuntimeInfo | MediaNative


__all__ = [
    "FragmentStream",
    "InfoModel",
    "MediaNative",
    "NativeResponse",
    "RuntimeInfo",
    "coerce_runtime_info",
]
