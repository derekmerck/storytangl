"""Canonical journal fragment surface.

This module is the stable import home for repo-owned reusable fragment and hint
types. Legacy subpackages under ``tangl.journal`` re-export from here for
compatibility.
"""

from __future__ import annotations

from base64 import b64encode
from collections.abc import Mapping
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_serializer, model_validator

from tangl.core import BaseFragment, Registry, Selector
from tangl.journal.intent import Accepts, Blocker, KvRow, UIHints
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.type_hints import Identifier, Pathlike, StyleClass, StyleDict, StyleId, UnstructuredData


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
    """Canonical content-bearing journal fragment.

    ``source_id`` identifies the entity or edge that donated the content.
    ``origin_id`` records the producer/provenance trail inherited from
    :class:`BaseFragment`. Handlers that merely transport or defer fragments
    should preserve both. Compositors that synthesize replacement prose may use
    the composing cursor or source of the new composite instead.
    """

    fragment_type: Literal["content"] = "content"
    content: Any = None
    source_id: UUID | None = None
    content_format: str | None = Field(None, alias="format")
    presentation_hints: PresentationHints | None = Field(None, alias="hints")


class GroupFragment(BaseFragment, extra="allow"):
    """Relational overlay tying peer fragments together by identifier.

    ``zone_role`` annotates a ``group_type="zone"`` group with its semantic role
    (``"packet"``, ``"field"``, ...) for ports that style zones by role. ``hints``
    carries the same advisory presentation metadata as the other fragments.
    """

    fragment_type: Literal["group"] = "group"
    group_type: str | Enum | None = None
    member_ids: list[UUID] = Field(default_factory=list)
    zone_role: str | None = None
    presentation_hints: PresentationHints | None = Field(None, alias="hints")

    def members(self, registry: Registry[BaseFragment]) -> list[BaseFragment]:
        return [
            member
            for member_id in self.member_ids
            if (member := registry.get(member_id)) is not None
        ]


class PieceFragment(BaseFragment, extra="allow"):
    """Identified game piece: a tracked object the player can reference, place
    into a zone, or pick as a choice payload (candidate, document, token, asset).

    A stable ``piece_id`` (and ``uid``) let multi-envelope sequences update the
    same piece in place as it changes state or moves between zones. ``zone_ref``
    names the containing ``group_type="zone"`` fragment. ``properties`` carries
    per-kind structured data (a candidate's declared purpose, a permit's expiry,
    ...). Python uses ``piece_kind`` because constructor-form persistence reserves
    ``kind`` for the model class; DTO projection exposes it as contract field
    ``kind``. Graduates the typed shape tracked as the ``PieceFragment`` row in
    ``WIDGET_CONTRACT_RECONCILIATION.md``; matches the existing conformance
    fixture shape.
    """

    fragment_type: Literal["piece"] = "piece"
    piece_id: str
    piece_kind: str = Field(
        ...,
        validation_alias=AliasChoices("piece_kind", "kind"),
        json_schema_extra={"dto": True, "dto_alias": "kind"},
    )
    display_state: str | None = None
    zone_ref: UUID | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    presentation_hints: PresentationHints | None = Field(None, alias="hints")


class KvFragment(BaseFragment, extra="allow", arbitrary_types_allowed=True):
    """Ordered key-value fragment for info-like surfaces."""

    fragment_type: Literal["kv"] = "kv"
    content: list[KvRow] = Field(default_factory=list)


class ChoiceFragment(BaseFragment, extra="allow"):
    """Direct, UUID-backed action offered to a client."""

    fragment_type: Literal["choice"] = "choice"
    edge_id: UUID
    text: str = ""
    available: bool = True
    unavailable_reason: str | None = None
    blockers: list[Blocker] | None = None
    accepts: Accepts | None = None
    ui_hints: UIHints | None = None
    activation_payload: Any = Field(None, alias="payload")


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
        return registry.find_one(Selector.from_identifier(self.reference_id))


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
    fragment_type: Literal["media"] = "media"

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


_FRAGMENT_DTO_TYPES: dict[str, type[BaseFragment]] = {
    "attributed": AttributedFragment,
    "block": BlockFragment,
    "choice": ChoiceFragment,
    "content": ContentFragment,
    "delete": ControlFragment,
    "dialog": DialogFragment,
    "group": GroupFragment,
    "kv": KvFragment,
    "media": MediaFragment,
    "piece": PieceFragment,
    "update": ControlFragment,
}


def fragment_to_dto(
    fragment: BaseFragment,
    *,
    exclude: set[str] | None = None,
) -> UnstructuredData:
    """Return the client DTO projection of a journal fragment.

    DTO projection is distinct from :meth:`unstructure`: it is JSON-safe,
    keyed by ``fragment_type``, and selected through ``dto_exclude`` field
    metadata rather than persistence's constructor-form ``kind`` path.
    """

    exclude_fields = set(fragment._match_fields(dto_exclude=True))
    if exclude is not None:
        exclude_fields.update(exclude)
    payload = fragment.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
        exclude=exclude_fields,
    )
    payload.pop("step", None)
    if payload.get("type") == payload.get("fragment_type"):
        payload.pop("type")
    if payload.get("tags") == []:
        payload.pop("tags")
    for field_name in fragment._match_fields(dto=True):
        dto_alias = type(fragment).model_fields[field_name].json_schema_extra["dto_alias"]
        if field_name in payload:
            payload[dto_alias] = payload.pop(field_name)
    return payload


def fragment_from_dto(payload: object) -> BaseFragment:
    """Hydrate a fragment DTO, preserving unknown extension fragments."""

    if not isinstance(payload, Mapping):
        return BaseFragment(fragment_type="unknown", content=payload)

    raw_fragment = dict(payload)
    fragment_type = raw_fragment.get("fragment_type")
    if not isinstance(fragment_type, str) or not fragment_type:
        return BaseFragment(fragment_type="unknown", content=raw_fragment)

    fragment_model = _FRAGMENT_DTO_TYPES.get(fragment_type)
    if fragment_model is None:
        return BaseFragment(fragment_type=fragment_type, content=raw_fragment)

    for field_name in fragment_model._match_fields(dto=True):
        dto_alias = fragment_model.model_fields[field_name].json_schema_extra["dto_alias"]
        if dto_alias in raw_fragment:
            raw_fragment[field_name] = raw_fragment.pop(dto_alias)
    return fragment_model.model_validate(raw_fragment)


__all__ = [
    "AttributedFragment",
    "BlockFragment",
    "Blocker",
    "ChoiceFragment",
    "ContentFragment",
    "ContentFormatType",
    "ControlFragment",
    "ControlFragmentType",
    "DialogFragment",
    "GroupFragment",
    "KvFragment",
    "KvRow",
    "MediaFragment",
    "PieceFragment",
    "PresentationHints",
    "StagingHints",
    "UIHints",
    "fragment_from_dto",
    "fragment_to_dto",
]
