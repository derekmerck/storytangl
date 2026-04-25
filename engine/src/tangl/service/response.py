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
    ValidationError,
    field_serializer,
    model_validator,
)

from tangl.core import BaseFragment
from tangl.info import __url__
from tangl.journal.fragments import KvFragment, MediaFragment, PresentationHints
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


class RuntimeEnvelope(InfoModel):
    """Ordered-fragment runtime payload for vm/story clients."""

    cursor_id: UUID | None = None
    step: int | None = None
    fragments: list[BaseFragment] = Field(default_factory=list)
    last_redirect: dict[str, Any] | None = None
    redirect_trace: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


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


JsonValue: TypeAlias = PydanticJsonValue


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


PrimitiveValue: TypeAlias = str | int | float | bool


class ScalarValue(BaseModel):
    """Single scalar projected-state payload."""

    value_type: Literal["scalar"] = "scalar"
    value: PrimitiveValue


class ProjectedKVItem(BaseModel):
    """One projected key-value pair."""

    key: str
    value: PrimitiveValue


class KvListValue(BaseModel):
    """Ordered key-value payload."""

    value_type: Literal["kv_list"] = "kv_list"
    items: list[ProjectedKVItem]


class ProjectedItem(BaseModel):
    """One projected list entry."""

    label: str
    detail: str | None = None
    tags: list[str] = Field(default_factory=list)


class ItemListValue(BaseModel):
    """Ordered projected item list."""

    value_type: Literal["item_list"] = "item_list"
    items: list[ProjectedItem]


class TableValue(BaseModel):
    """Tabular projected-state payload."""

    value_type: Literal["table"] = "table"
    columns: list[str]
    rows: list[list[PrimitiveValue]]

    @model_validator(mode="after")
    def _validate_row_lengths(self) -> Self:
        expected_width = len(self.columns)
        for index, row in enumerate(self.rows):
            if len(row) != expected_width:
                raise ValueError(
                    "table row "
                    f"{index} has {len(row)} values but expected {expected_width} "
                    "to match the declared columns"
                )
        return self


class BadgeListValue(BaseModel):
    """Badge or label collection payload."""

    value_type: Literal["badges"] = "badges"
    items: list[str]


SectionValue: TypeAlias = Annotated[
    ScalarValue | KvListValue | ItemListValue | TableValue | BadgeListValue,
    Field(discriminator="value_type"),
]


class ProjectedSection(BaseModel):
    """One ordered projected runtime-state section."""

    section_id: str
    title: str
    kind: str | None = None
    value: SectionValue
    hints: PresentationHints | None = None


class ProjectedState(InfoModel):
    """Canonical ordered projected-state payload for runtime surfaces."""

    sections: list[ProjectedSection] = Field(default_factory=list)


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
NativeResponse: TypeAlias = FragmentStream | RuntimeEnvelope | InfoModel | RuntimeInfo | MediaNative

__all__ = [
    "AuthoringDiagnostic",
    "BadgeListValue",
    "FragmentStream",
    "InfoModel",
    "ItemListValue",
    "KvListValue",
    "MediaNative",
    "NativeResponse",
    "PreflightReport",
    "PrimitiveValue",
    "ProjectedItem",
    "ProjectedKVItem",
    "ProjectedSection",
    "ProjectedState",
    "RuntimeEnvelope",
    "RuntimeInfo",
    "ScalarValue",
    "SectionValue",
    "SystemInfo",
    "TableValue",
    "UserInfo",
    "UserSecret",
    "WorldInfo",
    "WorldList",
    "WorldSceneList",
    "coerce_runtime_info",
]
