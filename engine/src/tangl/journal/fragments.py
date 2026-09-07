"""Canonical journal fragment surface.

This module is the stable import home for repo-owned reusable fragment and hint
types. Legacy subpackages under ``tangl.journal`` re-export from here for
compatibility.
"""

from __future__ import annotations

from base64 import b64encode
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import (
    AliasChoices,
    Field,
    field_serializer,
    model_validator,
)

from tangl.core import BaseFragment, Graph, Registry, Selector
from tangl.presentation.hints import PresentationHints, StagingHints
from tangl.presentation.intent import Accepts, Blocker, KvRow, UIHints
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.type_hints import Identifier, Pathlike, UnstructuredData


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


class JournalMarkerFragment(BaseFragment, extra="allow"):
    """Point marker used to compute journal slices at read time.

    Markers are stored in the same stream as presentation fragments so replay,
    persistence, and provenance stay unified. They mark a start point; spans are
    computed by :class:`tangl.vm.runtime.ledger.Ledger`.
    """

    fragment_type: Literal["marker"] = "marker"
    marker_type: str
    marker_name: str | None = None
    path: str | None = None


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
    available: bool = True
    """Render disabled when False -- a piece present but not selectable now.

    Mirrors :class:`ChoiceFragment`. A ``pieces`` choice constrained to a zone
    offers whatever that zone holds, so a spent or blocked member has to say so
    here; otherwise the only way a player learns it was unselectable is the
    error raised after committing it (widget vocabulary §7.1).
    """

    unavailable_reason: str | None = None


class KvFragment(BaseFragment, extra="allow", arbitrary_types_allowed=True):
    """Ordered key-value fragment for info-like surfaces."""

    fragment_type: Literal["kv"] = "kv"
    content: list[KvRow] = Field(default_factory=list)


UI_TAG_PREFIX = "ui:"


def client_visible_tags(tags: object) -> set[str]:
    """Return the ``ui:``-namespaced subset of ``tags``.

    Graph-side tags are mostly engine internals — ``dynamic``, ``sandbox``,
    ``movement``, ``fanout:<uuid>`` — and one of them carries graph identity, so
    promotion onto a client-facing fragment is opt-in by namespace rather than
    by omission. An author or mechanic that wants a tag to reach clients says so
    by naming it, and everything else stays inside the graph.

    This extends the convention already read off fragment tags by
    :meth:`tangl.core.BaseFragment.has_channel`, which spells its own namespace
    ``channel:``. Non-string tags (:data:`tangl.type_hints.Tag` also admits
    enums and ints) cannot carry a namespace and are dropped.
    """

    if not isinstance(tags, (set, frozenset, list, tuple)):
        return set()
    return {
        tag for tag in tags if isinstance(tag, str) and tag.startswith(UI_TAG_PREFIX)
    }


class ChoiceFragment(BaseFragment, extra="allow"):
    """Direct, UUID-backed action offered to a client."""

    fragment_type: Literal["choice"] = "choice"
    edge_id: UUID
    text: str = ""
    available: bool = True
    unavailable_reason: str | None = None
    blockers: list[Blocker] | None = None
    accepts: Accepts | None = Field(
        None, json_schema_extra={"unstructurable": True}
    )
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


ContentFormatType = Literal["url", "data", "xml", "json", "rit"]


class MediaFragment(ContentFragment, extra="allow"):
    """Media fragment that defers dereference and transport shaping to service."""

    content_type: MediaDataType = MediaDataType.MEDIA
    content: MediaRIT | Pathlike | bytes | str | dict
    content_format: ContentFormatType
    rit_id: UUID | None = None
    staging_hints: StagingHints | None = None
    media_role: str | None = None
    scope: str | None = "world"
    fragment_type: Literal["media"] = "media"

    @model_validator(mode="before")
    @classmethod
    def _capture_rit_reference(cls, data: Any) -> Any:
        """Record graph-owned RIT identity while fresh fragments carry the object."""

        if not isinstance(data, dict):
            return data
        payload = dict(data)
        content = payload.get("content")
        if payload.get("content_format") == "rit" and isinstance(content, MediaRIT):
            rit_id = payload.get("rit_id")
            if rit_id is not None and UUID(str(rit_id)) != content.uid:
                raise ValueError("MediaRIT content and rit_id must refer to the same resource")
            payload["rit_id"] = content.uid
        return payload

    def unstructure(self) -> UnstructuredData:
        """Persist generated media as a graph RIT reference, never a detached copy."""

        data = super().unstructure()
        if self.content_format == "rit":
            if self.rit_id is None:
                raise ValueError("RIT media fragments require a MediaRIT reference")
            data.pop("content", None)
            data["rit_id"] = self.rit_id
        return data

    @classmethod
    def structure(
        cls,
        data: UnstructuredData,
        _ctx: Graph | None = None,
    ) -> "MediaFragment":
        """Rebind persisted RIT media through the restored owning graph."""

        payload = dict(data)
        if payload.get("content_format") == "rit" and "content" not in payload:
            rit_id = payload.get("rit_id")
            if rit_id is None:
                raise ValueError("Restoring RIT media fragments requires a RIT reference")
            if _ctx is None:
                raise ValueError("Restoring RIT media fragments requires an owning graph")
            if not isinstance(rit_id, UUID):
                rit_id = UUID(str(rit_id))
            rit = _ctx.get(rit_id)
            if not isinstance(rit, MediaRIT):
                raise LookupError(f"Media fragment RIT {rit_id} is not present in the graph")
            payload["content"] = rit
        return super().structure(payload, _ctx=_ctx)

    def evolve(self, **updates: Any) -> Self:
        """Copy a live fragment without serializing its graph-owned RIT."""

        data = {**self.__dict__, **(self.__pydantic_extra__ or {}), **updates}
        if "content" in updates and "rit_id" not in updates:
            data["rit_id"] = None
        return type(self).model_validate(data)

    @field_serializer("content")
    def _encode_binary_content(self, content: Any) -> str:
        """Serialize content by format, never by falling back to ``repr``.

        A graph-owned :class:`MediaRIT` has no JSON encoder, so the bare
        ``str(content)`` below rendered its whole repr -- which reached text
        clients as narrative prose. Clients dereference media through
        ``rit_id`` and the service media path, so the serialized form only
        needs to name the resource. Persistence is unaffected either way:
        :meth:`unstructure` drops ``content`` for RIT media entirely and
        :meth:`structure` rebinds it from the owning graph.
        """

        if self.content_format == "data" and isinstance(content, bytes):
            return b64encode(content).decode("utf-8")
        if self.content_format == "rit" and isinstance(content, MediaRIT):
            return _rit_display_name(content)
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
    "marker": JournalMarkerFragment,
    "media": MediaFragment,
    "piece": PieceFragment,
    "update": ControlFragment,
}


def _rit_display_name(rit: MediaRIT) -> str:
    """Human-readable name for a media resource, for text-floor clients."""

    if rit.label and rit.label.strip():
        return rit.label.strip()
    if rit.path is not None:
        return Path(rit.path).name
    return str(rit.uid)


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
    "ChoiceFragment",
    "ContentFragment",
    "ContentFormatType",
    "ControlFragment",
    "ControlFragmentType",
    "DialogFragment",
    "GroupFragment",
    "JournalMarkerFragment",
    "KvFragment",
    "MediaFragment",
    "PieceFragment",
    "UI_TAG_PREFIX",
    "client_visible_tags",
    "fragment_from_dto",
    "fragment_to_dto",
]
