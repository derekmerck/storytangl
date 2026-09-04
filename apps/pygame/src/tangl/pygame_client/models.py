"""Adapter-local turn model for the pygame client.

Deliberately a sibling of ``tangl.renpy.models`` rather than a shared type. The
two ports need a second consumer before an adapter layer is worth extracting;
divergences between them are recorded in ``apps/pygame/README.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from tangl.journal.intent import Accepts
from tangl.service.response import JsonValue


@dataclass(slots=True, frozen=True)
class StageImage:
    """One image to draw, keyed by ``media_role`` rather than world identity."""

    role: str
    source: str
    alt_text: str | None = None
    source_id: UUID | None = None
    x_slot: str | None = None
    """From ``staging_hints.media_x``; ``None`` falls back to arrival order."""

    flip_h: bool = False
    """From ``staging_hints.media_flip_h``. Other staging hints are ignored by
    this port; honouring a subset is expected of a conforming client."""


@dataclass(slots=True, frozen=True)
class Line:
    """One narration or attributed line.

    ``speaker is None`` means narration and renders in the narration box;
    a speaker renders as a dialog bubble.
    """

    text: str
    speaker: str | None = None
    manner: str | None = None


@dataclass(slots=True, frozen=True)
class Choice:
    """One selectable choice.

    ``edge_id`` is the only thing the input layer ever commits, so a map
    hotspot resolves to the same payload as the numbered list (Input Parity).
    """

    edge_id: UUID
    text: str
    available: bool = True
    unavailable_reason: str | None = None
    payload: JsonValue | None = None
    tags: frozenset[str] = frozenset()
    """Client-visible ``ui:`` tags. A choice claiming ``ui:plate:<plate>:<region>``
    is the one a hitbox on that region commits."""

    accepts: Accepts | None = None
    """What this choice wants before it can be committed. ``None`` and
    ``kind="pick"`` both mean the edge id is the whole answer; every other kind
    needs a value collected first (widget vocabulary §6.1.1)."""


@dataclass(slots=True, frozen=True)
class Piece:
    """One identified game piece a choice may ask the player to select.

    ``piece_id`` is the world-facing handle a ``pieces`` payload names; the
    fragment ``uid`` is journal identity and stays out of the commit.
    """

    piece_id: str
    kind: str
    text: str
    label: str | None = None
    zone_ref: UUID | None = None
    available: bool = True
    unavailable_reason: str | None = None


@dataclass(slots=True, frozen=True)
class Finding:
    """One key/value row of disclosed state.

    ``emphasis`` is the engine's own severity word (``ok``/``warn``/``danger``/
    ``subtle``); the client picks a colour for it and never re-derives severity
    from the text.
    """

    key: str
    value: str
    emphasis: str | None = None


@dataclass(slots=True, frozen=True)
class Zone:
    """A container fragment pieces belong to.

    An empty zone is still worth drawing: a targetable zone with nothing in it
    is information, not an absence.
    """

    uid: UUID
    role: str | None = None
    label: str | None = None


@dataclass(slots=True, frozen=True)
class MapRegion:
    """One named hitbox, in fractions of the plate."""

    name: str
    x: float
    y: float
    w: float
    h: float


@dataclass(slots=True, frozen=True)
class MapPlate:
    """A visual map: a named image and the regions drawn on it.

    Geometry only. Which regions are live this turn is decided by intersecting
    region names against the choice list, never by anything stored here — so a
    plate is stable reference data that outlives any single turn.
    """

    name: str
    image: str | None = None
    regions: tuple[MapRegion, ...] = ()

    def claim(self, region: MapRegion) -> str:
        """Return the tag a choice must carry to own ``region`` on this plate."""

        return f"ui:plate:{self.name}:{region.name}"


@dataclass(slots=True)
class Turn:
    """One step's worth of images, lines, pieces, and choices."""

    step: int
    images: list[StageImage] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    choices: list[Choice] = field(default_factory=list)
    pieces: list[Piece] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    plate: MapPlate | None = None
    """Set from story-info rather than from fragments: geometry is disclosed
    state, not part of the turn's content."""


# ── input actions ────────────────────────────────────────────────────────────
#
# A click or key resolves to one of these rather than straight to a commit. A
# typed choice needs a value collected before it can go on the wire, and that
# collection is client-local: only ``Commit`` ever reaches the service, and it
# carries exactly what the CLI would send for the same choice (Input Parity,
# widget vocabulary §5.3).


@dataclass(slots=True, frozen=True)
class Commit:
    """Resolve a choice. The only action that reaches the service."""

    edge_id: UUID
    payload: JsonValue


@dataclass(slots=True, frozen=True)
class BeginSelection:
    """Start collecting values for a typed choice. Client-local."""

    choice: "Choice"


@dataclass(slots=True, frozen=True)
class PickPiece:
    """Add one piece to the pending selection. Client-local."""

    piece_id: str


@dataclass(slots=True, frozen=True)
class CancelSelection:
    """Abandon the pending selection. Client-local.

    Reachable by click as well as by key: a selection a mouse can enter but only
    a keyboard can leave is not a usable surface.
    """


Action = Commit | BeginSelection | PickPiece | CancelSelection


@dataclass(slots=True)
class PendingSelection:
    """A typed choice waiting for the values it needs before it can commit."""

    choice: Choice
    picked: list[str] = field(default_factory=list)

    @property
    def wanted(self) -> int:
        """How many pieces this choice still needs at minimum."""

        return max(self.choice.accepts.min - len(self.picked), 0)

    @property
    def full(self) -> bool:
        return len(self.picked) >= self.choice.accepts.max
