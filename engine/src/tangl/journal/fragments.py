"""Canonical journal fragment surface.

This module is the stable import home for repo-owned reusable fragment and hint
types. Legacy subpackages under ``tangl.journal`` re-export from here for
compatibility.
"""

from __future__ import annotations

from base64 import b64encode
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from tangl.core import BaseFragment, Registry
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.type_hints import Identifier, Pathlike, StyleClass, StyleDict, StyleId, UnstructuredData
from tangl.utils.ordered_tuple_dict import OrderedTupleDict


class PresentationHints(BaseModel, extra="allow"):
    """Advisory styling metadata for text and projected-state payloads."""

    model_config = ConfigDict(frozen=True)

    style_name: StyleId | None = None
    style_tags: list[StyleClass] = Field(default_factory=list)
    style_dict: StyleDict = Field(default_factory=dict)
    icon: str | None = None

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class ContentFragment(BaseFragment):
    """Canonical content-bearing journal fragment."""

    fragment_type: str | Enum = "content"
    content: Any = None
    source_id: UUID | None = None
    content_format: str | None = Field(None, alias="format")
    presentation_hints: PresentationHints | None = Field(None, alias="hints")


class GroupFragment(BaseFragment, extra="allow"):
    """Relational overlay tying peer fragments together by identifier."""

    fragment_type: Literal["group"] = "group"
    group_type: str | Enum | None = None
    member_ids: list[UUID] = Field(default_factory=list)

    def members(self, registry: Registry[BaseFragment]) -> list[BaseFragment]:
        return [
            member
            for member_id in self.member_ids
            if (member := registry.get(member_id)) is not None
        ]


class KvFragment(BaseFragment, extra="allow", arbitrary_types_allowed=True):
    """Ordered key-value fragment for info-like surfaces."""

    fragment_type: Literal["kv"] = "kv"
    content: OrderedTupleDict = Field(...)


class ChoiceFragment(BaseFragment, extra="allow"):
    """Choice fragment supporting both current and legacy field shapes."""

    fragment_type: Literal["choice"] = "choice"
    edge_id: UUID | None = None
    text: str = ""
    available: bool = True
    active: bool | None = None
    unavailable_reason: str | None = None
    blockers: list[dict[str, Any]] | None = None
    accepts: dict[str, Any] | None = None
    ui_hints: dict[str, Any] | None = None
    activation_payload: Any = Field(None, alias="payload")

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        content = payload.get("content")
        text = payload.get("text")
        active = payload.get("active")

        if not text and isinstance(content, str):
            payload["text"] = content
        if content is None and isinstance(payload.get("text"), str):
            payload["content"] = payload["text"]
        if "available" not in payload and active is not None:
            payload["available"] = bool(active)
        if "active" not in payload:
            payload["active"] = bool(payload.get("available", True))

        return payload


ControlFragmentType = Literal["update", "delete"]


class ControlFragment(BaseFragment, extra="allow"):
    """Reference-style fragment for update and delete control events."""

    fragment_type: ControlFragmentType = "update"
    reference_type: str | Enum = Field("content", alias="ref_type")
    reference_id: Identifier = Field(..., alias="ref_id")
    payload: UnstructuredData | None = None

    @model_validator(mode="after")
    def _validate_payload(self) -> "ControlFragment":
        if self.fragment_type == "update" and self.payload is None:
            raise ValueError("payload cannot be None for an update fragment")
        return self

    def reference(self, registry: Registry[BaseFragment]) -> BaseFragment:
        return registry.find_one(identifier=self.reference_id)


class UserEventFragment(BaseFragment, extra="allow"):
    """User-facing event fragment for notifications or client hints."""

    fragment_type: Literal["user_event"] = "user_event"
    event_type: str | None = None


ShapeName = Literal["landscape", "portrait", "square", "avatar", "banner", "bg"]
PositionName = Literal["top", "bottom", "left", "right", "cover", "inline"]
SizeName = Literal["small", "medium", "large"]
TransitionName = Literal[
    "fade_in",
    "fade_out",
    "remove",
    "from_right",
    "from_left",
    "from_top",
    "from_bottom",
    "to_right",
    "to_left",
    "to_top",
    "to_bottom",
    "update",
    "scale",
    "rotate",
]
DurationName = Literal["short", "medium", "long"]
TimingName = Literal["start", "stop", "pause", "restart", "loop"]


class StagingHints(BaseModel, extra="allow"):
    """Client-facing media staging hints."""

    media_shape: ShapeName | float | None = None
    media_size: SizeName | tuple[int, int] | tuple[float, float] | float | None = None
    media_position: PositionName | tuple[int, int] | tuple[float, float] | None = None
    media_transition: TransitionName | None = None
    media_duration: DurationName | float | None = None
    media_timing: TimingName | None = None


ContentFormatType = Literal["url", "data", "xml", "json", "rit"]


class MediaFragment(ContentFragment, extra="allow"):
    """Media fragment that defers dereference and transport shaping to service."""

    content_type: MediaDataType = MediaDataType.MEDIA
    content: Pathlike | bytes | str | dict | MediaRIT
    content_format: ContentFormatType
    staging_hints: StagingHints | None = None
    media_role: str | None = None
    scope: str | None = "world"
    fragment_type: str = "media"

    @field_serializer("content")
    def _encode_binary_content(self, content: Any) -> str:
        if self.content_format == "data" and isinstance(content, bytes):
            return b64encode(content).decode("utf-8")
        return str(content)


class AttributedFragment(ContentFragment, extra="allow"):
    """Content fragment annotated with dialog-style speaker metadata."""

    fragment_type: Literal["attributed"] = Field("attributed", alias="type")
    who: str
    how: str
    media: str


class DialogFragment(GroupFragment, extra="allow"):
    """Compatibility dialog container fragment."""

    fragment_type: Literal["dialog"] = "dialog"
    content: list[AttributedFragment] = Field(default_factory=list)


class BlockFragment(ContentFragment):
    """Compatibility block fragment carrying nested choices."""

    fragment_type: Literal["block"] = "block"
    choices: list[ChoiceFragment] = Field(default_factory=list)


__all__ = [
    "AttributedFragment",
    "BlockFragment",
    "ChoiceFragment",
    "ContentFragment",
    "ContentFormatType",
    "ControlFragment",
    "ControlFragmentType",
    "DialogFragment",
    "GroupFragment",
    "KvFragment",
    "MediaFragment",
    "PresentationHints",
    "StagingHints",
    "UserEventFragment",
]
