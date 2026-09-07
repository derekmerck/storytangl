"""Service-native response primitives."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Mapping, Optional, Self, TypeAlias
from uuid import UUID

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue as PydanticJsonValue,
    SerializeAsAny,
    StringConstraints,
    ValidationError,
    field_validator,
    field_serializer,
)

from tangl.core import BaseFragment
from tangl.info import __url__
from tangl.presentation import events as _presentation_events
from tangl.presentation import projection as _presentation_projection
from tangl.journal.fragments import (
    KvFragment,
    MediaFragment,
    fragment_to_dto,
)
from tangl.service.user.user import User


class InfoModel(BaseModel):
    """Marker base for service information payloads."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RuntimeInfo(InfoModel):
    """Service runtime acknowledgement payload."""

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


JsonValue: TypeAlias = PydanticJsonValue


class RuntimeMetadata(InfoModel):
    """Typed reserved envelope metadata with open extension fields."""

    model_config = ConfigDict(extra="allow")

    grammar: _presentation_events.GrammarHint | None = None


class RuntimeEnvelopePayload(InfoModel):
    """Transport schema for :meth:`RuntimeEnvelope.to_dto` output."""

    model_config = ConfigDict(extra="allow")

    cursor_id: UUID | None = None
    step: int | None = None
    fragments: list[dict[str, JsonValue]] = Field(default_factory=list)
    ux_events: list[_presentation_events.UxEvent] = Field(default_factory=list)
    last_redirect: dict[str, JsonValue] | None = None
    redirect_trace: list[dict[str, JsonValue]] = Field(default_factory=list)
    metadata: RuntimeMetadata = Field(default_factory=RuntimeMetadata)


class RuntimeEnvelope(InfoModel):
    """Ordered-fragment runtime payload for vm/story clients."""

    cursor_id: UUID | None = None
    step: int | None = None
    fragments: list[SerializeAsAny[BaseFragment]] = Field(default_factory=list)
    ux_events: list[_presentation_events.UxEvent] = Field(default_factory=list)
    last_redirect: dict[str, Any] | None = None
    redirect_trace: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def _hydrate_reserved_metadata(cls, metadata: dict[str, Any]) -> dict[str, Any]:
        if "grammar" not in metadata:
            return metadata
        return {
            **metadata,
            "grammar": _presentation_events.GrammarHint.model_validate(metadata["grammar"]),
        }

    def to_dto(self) -> dict[str, Any]:
        """Return the transport DTO projection for client-facing envelopes."""

        base_payload = self.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
            exclude={"fragments"},
        )
        payload: dict[str, Any] = {}
        for field_name in ("cursor_id", "step"):
            if field_name in base_payload:
                payload[field_name] = base_payload.pop(field_name)
        payload["fragments"] = [fragment_to_dto(fragment) for fragment in self.fragments]
        payload.update(base_payload)
        return payload


class CommandEdgeQuery(InfoModel):
    """Find an actionable edge from player-authored command text."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    kind: Literal["command"] = "command"
    command: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


EdgeQuery: TypeAlias = CommandEdgeQuery


class DirectEdgeRequest(InfoModel):
    """Resolve one already-selected edge."""

    model_config = ConfigDict(extra="forbid")

    edge_id: UUID
    payload: JsonValue | None = None


class FindEdgeRequest(InfoModel):
    """Find and resolve an edge from a typed query."""

    model_config = ConfigDict(extra="forbid")

    find_edge: EdgeQuery
    payload: JsonValue | None = None


EdgeResolutionRequest: TypeAlias = DirectEdgeRequest | FindEdgeRequest


class SystemInfo(InfoModel):
    engine: str
    version: str
    uptime: str
    worlds: list[str] | int
    num_users: int
    homepage_url: AnyUrl = __url__

    @field_serializer("homepage_url")
    @classmethod
    def serialize_homepage(cls, value: AnyUrl, _info):
        return str(value)


class UserInfo(InfoModel):
    user_id: UUID
    user_secret: str
    created_dt: datetime
    last_played_dt: Optional[datetime] = None
    worlds_played: set[str]
    stories_finished: int = 0
    turns_played: int = 0
    achievements: Optional[set[str]] = None

    @classmethod
    def from_user(cls, user: User, **kwargs: object) -> Self:
        return cls(
            user_id=user.uid,
            user_secret=getattr(user, "secret", ""),
            created_dt=user.created_dt,
            last_played_dt=user.last_played_dt,
            worlds_played=set(getattr(user, "worlds_played", set())),
            stories_finished=getattr(user, "stories_finished", 0),
            turns_played=getattr(user, "turns_played", 0),
            achievements=set(getattr(user, "achievements", set())) or None,
            **kwargs,
        )


class UserSecret(InfoModel):
    """API-key material returned for user bootstrap and secret rotation."""

    api_key: str
    user_secret: str
    user_id: UUID | None = None


class WorldInfo(InfoModel):
    label: str
    title: str | None = None
    author: str | None = None


class AuthoringDiagnostic(InfoModel):
    """Common service-facing shape for authoring integrity diagnostics."""

    phase: Literal["decode", "compile", "runtime"]
    severity: Literal["error", "warning"]
    code: str
    message: str
    source: dict[str, JsonValue] | None = None
    subject_label: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class PreflightReport(InfoModel):
    """Non-mutating world authoring-integrity report."""

    world_id: str
    status: Literal["ok", "error"]
    diagnostics: list[AuthoringDiagnostic] = Field(default_factory=list)


class WorldList(KvFragment):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"key": "TangldWorld", "value": "my_world", "style_hints": {"color": "orange"}},
        }
    )


class WorldSceneList(KvFragment):
    ...


def coerce_runtime_info(value: Any) -> RuntimeInfo | None:
    """Best-effort coercion from runtime-like payloads to ``RuntimeInfo``."""

    if isinstance(value, RuntimeInfo):
        return value

    # Preserve runtime details payloads (for example hydrated ledger objects)
    # when converting sibling runtime model classes.
    if hasattr(value, "status") and hasattr(value, "details"):
        try:
            return RuntimeInfo(
                status=getattr(value, "status"),
                code=getattr(value, "code", None),
                message=getattr(value, "message", None),
                cursor_id=getattr(value, "cursor_id", None),
                step=getattr(value, "step", None),
                details=getattr(value, "details", None),
            )
        except (TypeError, ValidationError):
            pass

    payload: dict[str, Any] | None = None
    if isinstance(value, Mapping):
        payload = dict(value)
    elif isinstance(value, BaseModel):
        try:
            payload = value.model_dump(mode="python")
        except TypeError:
            payload = None
    elif hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        try:
            payload = value.model_dump(mode="python")
        except TypeError:
            payload = None

    if payload is None or "status" not in payload:
        return None

    try:
        return RuntimeInfo.model_validate(payload)
    except ValidationError:
        return None


FragmentStream: TypeAlias = list[BaseFragment]
MediaNative: TypeAlias = MediaFragment
NativeResponse: TypeAlias = (
    FragmentStream
    | RuntimeEnvelope
    | _presentation_projection.ProjectedState
    | InfoModel
    | RuntimeInfo
    | MediaNative
)

__all__ = [
    "AuthoringDiagnostic",
    "CommandEdgeQuery",
    "DirectEdgeRequest",
    "EdgeQuery",
    "EdgeResolutionRequest",
    "FindEdgeRequest",
    "FragmentStream",
    "InfoModel",
    "JsonValue",
    "MediaNative",
    "NativeResponse",
    "PreflightReport",
    "RuntimeEnvelope",
    "RuntimeEnvelopePayload",
    "RuntimeInfo",
    "RuntimeMetadata",
    "SystemInfo",
    "UserInfo",
    "UserSecret",
    "WorldInfo",
    "WorldList",
    "WorldSceneList",
    "coerce_runtime_info",
]
