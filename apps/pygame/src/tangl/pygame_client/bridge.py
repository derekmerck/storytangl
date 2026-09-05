"""Session bridge from StoryTangl's service surface to the pygame turn model.

Imports no pygame, so the whole adaptation layer is testable under ordinary
pytest. The renderer lives in :mod:`tangl.pygame_client.stage`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from tangl.core import BaseFragment
from tangl.journal.fragments import (
    AttributedFragment,
    ChoiceFragment,
    ContentFragment,
    GroupFragment,
    KvFragment,
    MediaFragment,
    PieceFragment,
)
from tangl.persistence import PersistenceManagerFactory
from tangl.service.media import (
    MediaContentProfile,
    MediaPendingPolicy,
    MediaRenderProfile,
    media_fragment_to_payload,
)
from tangl.service.response import (
    DirectEdgeRequest,
    JsonValue,
    RuntimeEnvelope,
    RuntimeInfo,
)
from tangl.service.service_manager import ServiceManager

from .models import (
    Choice,
    Finding,
    Line,
    MapPlate,
    MapRegion,
    PendingSelection,
    Piece,
    StageImage,
    Turn,
    Zone,
)

logger = logging.getLogger(__name__)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


# ``content_format`` names the key its source lives under. This used to be a
# four-way probe because the service could hand back a dereferenced payload
# still labelled ``"rit"``, so no client could trust the declaration; now that
# every profile declares what it actually carries, the format is the lookup.
_SOURCE_KEY_BY_FORMAT = {"url": "url", "path": "path"}


def _payload_source(payload: dict[str, Any]) -> str | None:
    """Return the media source a payload declares, or None when it carries none."""

    key = _SOURCE_KEY_BY_FORMAT.get(str(payload.get("content_format")))
    if key is None:
        return None
    value = payload.get(key)
    if isinstance(value, Path):
        return str(value)
    return _text(value)


class UnsupportedAccepts(ValueError):
    """Raised for an ``accepts`` kind this port cannot collect a value for.

    Better than committing a guess: the CLI reference port refuses the same
    kinds unless handed an explicit payload, and a wrong payload shape reaches
    the player as an opaque backend error.
    """


def commit_payload(choice: Choice, values: Sequence[str] = ()) -> JsonValue:
    """Build the wire payload for ``choice``, keyed by ``accepts.kind``.

    Follows the payload table at widget vocabulary §6.1.1, so a hotspot and a
    numbered key commit the same thing and this port stays within the Input
    Parity rule (§5.3). It is not byte-identical to the CLI in every case: the
    CLI discards an authored activation payload and this port preserves it,
    which is a gap on that side rather than a divergence to copy.

    The return is not always a mapping -- a ``pick`` forwards a non-mapping
    activation payload verbatim -- so the type is the wire's, not a dict.

    Validation here is advisory. The backend re-checks and is authoritative
    (§6.1.2); refusing early only keeps a doomed commit off the wire.
    """

    accepts = choice.accepts
    kind = getattr(accepts, "kind", "pick") if accepts is not None else "pick"
    authored = choice.payload

    if kind == "pick":
        if values:
            raise UnsupportedAccepts("This choice does not accept an input value.")
        # An authored activation payload is the edge's own answer and travels
        # verbatim, including when it is not a mapping. The CLI drops it, which
        # is a gap on that side rather than a licence to drop it here.
        return {} if authored is None else authored

    if kind == "pieces":
        minimum, maximum = accepts.min, accepts.max
        if len(values) < minimum:
            raise UnsupportedAccepts(f"Select at least {minimum} piece(s).")
        if len(values) > maximum:
            raise UnsupportedAccepts(f"Select at most {maximum} piece(s).")
        return _merge_authored(authored, {"piece_ids": list(values)})

    # text, quantity, place and compose need input surfaces this port does not
    # have yet. Land them with the world that needs one, not speculatively.
    raise UnsupportedAccepts(f"This port cannot collect a {kind!r} value yet.")


def _merge_authored(authored: Any, collected: dict[str, Any]) -> dict[str, Any]:
    """Combine an authored activation payload with what the player supplied.

    Precedence is explicit: authored keys form the base, collected keys win. The
    player's answer to ``accepts`` is the thing the choice asked for, so it
    cannot be shadowed by a default the author set on the edge.

    A non-mapping activation payload cannot be merged with named values, so it
    is dropped rather than guessed at -- and that is worth knowing about.
    """

    if authored is None:
        return collected
    if not isinstance(authored, dict):
        logger.debug(
            "Dropping non-mapping activation payload %r for a typed choice", authored
        )
        return collected
    return {**authored, **collected}


def selectable_pieces(turn: Turn, choice: Choice) -> list[Piece]:
    """Return the pieces ``choice`` will accept, in stream order.

    Decision Legibility (§5.1): a choice constrained to a zone may only be
    satisfied by pieces the player can see in that zone, so the constraint is
    read here rather than left to the renderer to guess.
    """

    accepts = choice.accepts
    if getattr(accepts, "kind", None) != "pieces":
        return []
    # ``available=False`` is the piece saying it cannot satisfy a choice right
    # now, and that holds whether or not the choice narrows by zone.
    offered = [piece for piece in turn.pieces if piece.available]
    constraints = accepts.constraints
    if constraints is None:
        return offered
    zone_ref = constraints.target_zone_ref
    kinds = constraints.target_kind
    # ``available=False`` is the piece saying it cannot satisfy a choice right
    # now. Offering it anyway would put a guaranteed backend error behind a row
    # that looks perfectly selectable.
    return [
        piece
        for piece in offered
        if (zone_ref is None or str(piece.zone_ref) == zone_ref)
        and (kinds is None or piece.kind in kinds)
    ]


def remaining_pieces(turn: Turn, pending: PendingSelection) -> list[Piece]:
    """Pieces still on offer for a pending selection, in stream order.

    Already-picked pieces drop out so a ``max > 1`` selection cannot name the
    same piece twice, and so the numbered list the player reads always matches
    what is still choosable.
    """

    return [
        piece
        for piece in selectable_pieces(turn, pending.choice)
        if piece.piece_id not in pending.picked
    ]


def _step(fragment: BaseFragment) -> int:
    try:
        return max(int(getattr(fragment, "step", 0) or 0), 0)
    except (TypeError, ValueError):
        return 0


class PygameSessionBridge:
    """Own the story session and adapt envelopes into :class:`Turn` values."""

    def __init__(
        self,
        service_manager: ServiceManager | None = None,
        *,
        user_id: UUID | None = None,
        user_secret: str | None = None,
        media_render_profile: MediaRenderProfile | None = None,
    ) -> None:
        self.service_manager = service_manager or ServiceManager(
            PersistenceManagerFactory.native_in_mem()
        )
        self.user_id = user_id
        self.user_secret = user_secret
        self.ledger_id: UUID | None = None
        self.world_id: str | None = None
        self.media_render_profile = media_render_profile or MediaRenderProfile(
            pending_policy=MediaPendingPolicy.FALLBACK,
            content_profile=MediaContentProfile.PASSTHROUGH,
        )

    # ── session lifecycle ────────────────────────────────────────────────

    def start(self, world_id: str) -> RuntimeEnvelope:
        """Create a fresh story session for ``world_id``."""

        user_id = self._ensure_user_id()
        self.world_id = world_id
        envelope = self.service_manager.create_story(
            user_id=user_id,
            world_id=world_id,
        )
        self._sync(envelope)
        return envelope

    def choose(self, edge_id: UUID, payload: JsonValue | None = None) -> RuntimeEnvelope:
        """Commit one choice by edge id."""

        if self.user_id is None or self.ledger_id is None:
            raise RuntimeError("choose() requires an active story session")
        envelope = self.service_manager.resolve_choice(
            user_id=self.user_id,
            ledger_id=self.ledger_id,
            request=DirectEdgeRequest(edge_id=edge_id, payload=payload),
        )
        self._sync(envelope)
        return envelope

    def _ensure_user_id(self) -> UUID:
        """Register a session user; the service will not accept an invented id."""

        if self.user_id is not None:
            return self.user_id
        info = self.service_manager.create_user(secret=self.user_secret)
        if not isinstance(info, RuntimeInfo):
            raise TypeError(f"Expected RuntimeInfo from create_user(), got {type(info)!r}")
        raw = dict(info.details or {}).get("user_id")
        if raw is None:
            raise RuntimeError("create_user() did not return a user_id detail")
        self.user_id = raw if isinstance(raw, UUID) else UUID(str(raw))
        return self.user_id

    def _sync(self, envelope: RuntimeEnvelope) -> None:
        """Track the active ledger, which travels in envelope metadata."""

        raw = dict(envelope.metadata or {}).get("ledger_id")
        if raw is None:
            raise RuntimeError("RuntimeEnvelope metadata did not include ledger_id")
        self.ledger_id = raw if isinstance(raw, UUID) else UUID(str(raw))

    # ── disclosure ───────────────────────────────────────────────────────

    def map_plate(self) -> MapPlate | None:
        """Return the plate the cursor publishes, or None where there is no map.

        Plate geometry rides story-info rather than the journal because it is
        reference state, not turn content: it changes when the world's art
        changes, not when the reader moves. Requested by name so a client that
        cannot draw maps never pays for it.
        """

        if self.user_id is None or self.ledger_id is None:
            return None
        state = self.service_manager.get_story_info(
            user_id=self.user_id,
            ledger_id=self.ledger_id,
            kinds=["map_plate", "map_regions"],
        )
        sections = {
            section.get("section_id"): section
            for section in (state.to_dto().get("sections") or [])
        }
        summary = sections.get("sandbox_map_plate")
        if summary is None:
            return None
        rows = {
            row.get("key"): row.get("value")
            for row in (summary.get("value", {}).get("items") or [])
        }
        name = _text(rows.get("Name"))
        if name is None:
            return None
        return MapPlate(
            name=name,
            image=_text(rows.get("Image")),
            regions=self._regions(sections.get("sandbox_map_regions")),
        )

    @staticmethod
    def _regions(section: dict[str, Any] | None) -> tuple[MapRegion, ...]:
        """Read region rows, skipping any the table cannot express as numbers."""

        if section is None:
            return ()
        value = section.get("value") or {}
        columns = list(value.get("columns") or [])
        regions: list[MapRegion] = []
        for row in value.get("rows") or []:
            fields = dict(zip(columns, row))
            name = _text(fields.get("Region"))
            if name is None:
                continue
            try:
                regions.append(
                    MapRegion(
                        name=name,
                        x=float(fields["x"]),
                        y=float(fields["y"]),
                        w=float(fields["w"]),
                        h=float(fields["h"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                logger.debug("Unusable map region row: %r", row)
        return tuple(regions)

    # ── adaptation ───────────────────────────────────────────────────────

    def build_turns(self, fragments: list[BaseFragment]) -> list[Turn]:
        """Group fragments into per-step turns, in stream order."""

        turns: dict[int, Turn] = {}
        for fragment in self._flatten(fragments):
            step = _step(fragment)
            self._append(turns.setdefault(step, Turn(step=step)), fragment)
        return [turns[step] for step in sorted(turns)]

    def _flatten(self, fragments: list[BaseFragment]) -> list[BaseFragment]:
        """Flatten grouping fragments, keeping the ones that are not decoration.

        A ``zone`` is a container the player acts against -- a ``pieces`` choice
        names one in its constraints -- so it survives flattening. Every other
        grouping is presentational and its members stand on their own.
        """

        flat: list[BaseFragment] = []
        for fragment in fragments:
            if isinstance(fragment, GroupFragment):
                if fragment.group_type == "zone":
                    flat.append(fragment)
                flat.extend(self._flatten(list(fragment.content or [])))
                continue
            flat.append(fragment)
        return flat

    @staticmethod
    def _label(fragment: BaseFragment) -> str | None:
        hints = fragment.presentation_hints
        return None if hints is None else _text(getattr(hints, "label_text", None))

    def _append(self, turn: Turn, fragment: BaseFragment) -> None:
        if isinstance(fragment, ChoiceFragment):
            turn.choices.append(
                Choice(
                    edge_id=fragment.edge_id,
                    text=_text(fragment.text) or "(unnamed choice)",
                    available=fragment.available,
                    unavailable_reason=_text(fragment.unavailable_reason),
                    payload=fragment.activation_payload,
                    tags=frozenset(
                        tag
                        for tag in (getattr(fragment, "tags", None) or ())
                        if isinstance(tag, str)
                    ),
                    accepts=fragment.accepts,
                )
            )
            return

        if isinstance(fragment, PieceFragment):
            turn.pieces.append(
                Piece(
                    piece_id=fragment.piece_id,
                    kind=fragment.piece_kind,
                    text=_text(fragment.content) or "",
                    label=self._label(fragment),
                    zone_ref=fragment.zone_ref,
                    available=fragment.available,
                    unavailable_reason=_text(fragment.unavailable_reason),
                )
            )
            return

        if isinstance(fragment, KvFragment):
            turn.findings.extend(
                Finding(
                    key=str(row.key),
                    value=str(row.value),
                    emphasis=row.emphasis,
                )
                for row in fragment.content
            )
            return

        if isinstance(fragment, GroupFragment):
            turn.zones.append(
                Zone(
                    uid=fragment.uid,
                    role=_text(fragment.zone_role),
                    label=self._label(fragment),
                )
            )
            return

        if isinstance(fragment, MediaFragment):
            self._append_media(turn, fragment)
            return

        # AttributedFragment subclasses ContentFragment, so it is checked first.
        if isinstance(fragment, AttributedFragment):
            text = _text(fragment.content)
            if text is not None:
                turn.lines.append(
                    Line(
                        text=text,
                        speaker=_text(fragment.who),
                        manner=_text(fragment.how),
                    )
                )
            return

        if isinstance(fragment, ContentFragment):
            text = _text(fragment.content)
            if text is not None:
                turn.lines.append(Line(text=text))

    @staticmethod
    def _append_fallback_text(
        turn: Turn,
        payload: dict[str, Any] | None,
        fragment: MediaFragment,
    ) -> None:
        """Render whatever text stands in for media that cannot be shown."""

        text = None
        if payload is not None:
            text = _text(payload.get("content")) or _text(payload.get("text"))
        if text is None:
            text = _text(getattr(fragment, "text", None))
        if text is not None:
            turn.lines.append(Line(text=text))

    def _append_media(self, turn: Turn, fragment: MediaFragment) -> None:
        payload = media_fragment_to_payload(
            fragment,
            render_profile=self.media_render_profile,
            world_id=self.world_id,
        )
        if payload is None or payload.get("fragment_type") != "media":
            # Media that cannot be dereferenced degrades to its text floor. The
            # service may supply that text itself, so prefer the payload's.
            self._append_fallback_text(turn, payload, fragment)
            return

        source = _payload_source(payload)
        if source is None:
            logger.debug("Media payload without a usable source: %r", payload)
            self._append_fallback_text(turn, payload, fragment)
            return
        hints = fragment.staging_hints
        turn.images.append(
            StageImage(
                role=_text(payload.get("media_role")) or _text(fragment.media_role) or "media",
                source=source,
                alt_text=_text(payload.get("text")),
                source_id=getattr(fragment, "rit_id", None),
                x_slot=getattr(hints, "media_x", None),
                flip_h=bool(getattr(hints, "media_flip_h", None)),
            )
        )
