"""Canonical journal fragment surface.

This module is the stable import home for repo-owned reusable fragment types.
Presentation values belong to :mod:`tangl.presentation`; journal compatibility
subpackages re-export only fragment types.
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
from tangl.presentation.hints import PresentationHints as _PresentationHints
from tangl.presentation.hints import StagingHints as _StagingHints
from tangl.presentation.intent import Accepts as _Accepts
from tangl.presentation.intent import Blocker as _Blocker
from tangl.presentation.intent import UIHints as _UIHints
from tangl.presentation.values import KvRow as _KvRow
from tangl.presentation.targets import (
    FragmentTarget,
    PresentationTarget,
    RitTarget,
    RoleTarget,
)
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
    presentation_hints: _PresentationHints | None = Field(None, alias="hints")


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
    presentation_hints: _PresentationHints | None = Field(None, alias="hints")

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
    presentation_hints: _PresentationHints | None = Field(None, alias="hints")
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
    content: list[_KvRow] = Field(default_factory=list)


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
    blockers: list[_Blocker] | None = None
    accepts: _Accepts | None = Field(
        None, json_schema_extra={"unstructurable": True}
    )
    ui_hints: _UIHints | None = None
    activation_payload: Any = Field(None, alias="payload")


ControlFragmentType = Literal["update", "delete"]


class ControlFragment(BaseFragment, extra="allow"):
    """Reference-style fragment for update and delete control events."""

    fragment_type: ControlFragmentType = "update"
    target: PresentationTarget = Field(json_schema_extra={"unstructurable": True})
    payload: UnstructuredData | None = None
    patch_kind: Literal["content", "presentation"] = "content"
    media_action: Literal["restart"] | None = None
    media: MediaFragment | None = Field(None, json_schema_extra={"unstructurable": True})

    @model_validator(mode="after")
    def _validate_payload(self) -> "ControlFragment":
        if self.payload is not None:
            transport_fields = {
                "rit_id", "url", "path", "src", "content_type", "media_type",
                "media_format", "mime_type", "sprite_sheets",
            }
            if (
                transport_fields.intersection(self.payload)
                or self.payload.get("content_format", self.payload.get("format"))
                in ("url", "path", "data", "xml", "rit")
                or self.payload.get("fragment_type", self.payload.get("type")) == "media"
                or isinstance(self.payload.get("media"), (dict, MediaFragment, MediaRIT))
            ):
                raise ValueError("media descriptors belong in the typed media field, not payload")
            if self.patch_kind == "presentation" and self.payload.keys() - {
                "text", "fallback_text", "staging_hints", "presentation_hints", "hints",
                "media_role", "presentation_handle",
            }:
                raise ValueError(
                    "presentation patches contain only captions and presentation hints",
                )
        if self.media is not None:
            if (
                self.fragment_type != "update" or self.payload is not None
                or self.patch_kind != "content"
            ):
                raise ValueError("media update requires ordinary media, not a patch payload")
            if self.media_action == "restart" and self.media.rit_id is None:
                raise ValueError("restart media requires resource identity (rit_id)")
        elif self.media_action is not None:
            raise ValueError("restart requires update + ordinary media, not a patch payload")
        elif self.fragment_type == "update" and self.payload is None:
            raise ValueError("payload cannot be None for an update fragment")
        return self

    def matches(self, fragment: BaseFragment) -> bool:
        """Match current presentations, never source entities or cached bytes."""
        if isinstance(self.target, FragmentTarget):
            return fragment.uid == self.target.fragment_id
        if not isinstance(fragment, MediaFragment):
            return False
        if isinstance(self.target, RitTarget):
            return fragment.rit_id == self.target.rit_id
        if isinstance(self.target, RoleTarget):
            return fragment.media_role == self.target.media_role
        return fragment.presentation_handle == self.target.handle

    def references(self, registry: Registry[BaseFragment]) -> list[BaseFragment]:
        return list(registry.find_all(Selector(predicate=self.matches)))

    def apply_to(self, fragment: BaseFragment) -> BaseFragment | None:
        """Apply a matched registry edit without mutating history or upserting.

        Content/game patches never edit a media source. Presentation patches
        carry only per-use metadata; replacements carry a complete media value.
        Restart remains a live action for a later playback owner.
        """
        if not self.matches(fragment) or self.media_action is not None:
            return fragment
        if self.fragment_type == "delete":
            return None
        if self.media is not None:
            if not isinstance(fragment, MediaFragment):
                return fragment
            return self.media.evolve(uid=fragment.uid).continued_from(fragment)
        if isinstance(fragment, MediaFragment):
            if self.patch_kind != "presentation":
                return fragment
        updates = dict(self.payload)
        if self.patch_kind == "presentation":
            if isinstance(fragment, MediaFragment) and updates.get("staging_hints") is not None:
                previous = fragment.staging_hints.model_dump() if fragment.staging_hints else {}
                updates["staging_hints"] = {**previous, **updates["staging_hints"]}
            if isinstance(fragment, ContentFragment):
                if "presentation_hints" in updates:
                    updates.setdefault("hints", updates.pop("presentation_hints"))
                if updates.get("hints") is not None:
                    previous = (
                        fragment.presentation_hints.model_dump()
                        if fragment.presentation_hints else {}
                    )
                    updates["hints"] = {**previous, **updates["hints"]}
        return fragment.evolve(**{**updates, "uid": fragment.uid})


ContentFormatType = Literal["url", "path", "data", "xml", "json", "rit"]


class MediaFragment(ContentFragment, extra="allow"):
    """Media fragment that defers dereference and transport shaping to service."""

    content_type: MediaDataType = MediaDataType.MEDIA
    content: MediaRIT | Pathlike | bytes | str | dict
    content_format: ContentFormatType
    rit_id: UUID | None = None
    staging_hints: _StagingHints | None = None
    media_role: str | None = None
    presentation_handle: str | None = None
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
        data["hints"] = updates.get("hints", data.pop("presentation_hints"))
        if "content" in updates and "rit_id" not in updates:
            data["rit_id"] = None
        return type(self).model_validate(data)

    def continued_from(self, previous: MediaFragment | None) -> Self:
        """Inherit repetition only when restating the same identified resource."""
        if (
            previous is not None and self.rit_id is not None and self.rit_id == previous.rit_id
            and previous.staging_hints is not None
            and (self.staging_hints is None or self.staging_hints.media_timing is None)
        ):
            hints = self.staging_hints or _StagingHints()
            return self.evolve(staging_hints=hints.model_copy(update={
                "media_timing": previous.staging_hints.media_timing,
            }))
        return self

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

    content_format = raw_fragment.get("content_format")
    if fragment_type == "media" and content_format in {"url", "path", "data", "xml"}:
        source_key = "data" if content_format == "xml" else content_format
        raw_fragment.setdefault("content", raw_fragment.get(source_key))
        if "media_type" in raw_fragment:
            raw_fragment["content_type"] = raw_fragment.pop("media_type")
    if fragment_type == "update" and raw_fragment.get("media") is not None:
        raw_fragment["media"] = fragment_from_dto(raw_fragment["media"])

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
