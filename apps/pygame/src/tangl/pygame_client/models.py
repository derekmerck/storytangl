"""Adapter-local turn model for the pygame client.

Deliberately a sibling of ``tangl.renpy.models`` rather than a shared type. The
two ports need a second consumer before an adapter layer is worth extracting;
divergences between them are recorded in ``apps/pygame/README.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from tangl.presentation.intent import Accepts
from tangl.presentation.hints import TimingName
from tangl.presentation.sprite_sheet import SpriteSheetManifest
from tangl.service.response import JsonValue


@dataclass(slots=True, frozen=True)
class StageImage:
    """One image to draw, keyed by ``media_role`` rather than world identity."""

    role: str
    source: str
    alt_text: str | None = None
    source_id: UUID | None = None
    x_slot: str | None = None
    """From ``staging_hints.media_x`` when it names a slot.

    ``None`` falls back to arrival order. A numeric ``media_x`` sets
    :attr:`x_frac` instead, and leaves this ``None``.
    """

    y_slot: str | None = None
    """From ``staging_hints.media_y`` when it names a level. ``None`` takes the
    shared floor. A numeric ``media_y`` sets :attr:`y_frac` instead."""

    x_frac: float | None = None
    """From a numeric ``staging_hints.media_x``: where the image's horizontal
    centre goes, as a fraction of the stage's width.

    Centre rather than left edge, so a placement means the same thing whatever
    the image's width -- and so it agrees with the bottom-centre anchor a
    sprite sheet already uses. ``None`` means this image is slotted, not
    placed.
    """

    y_frac: float | None = None
    """From a numeric ``staging_hints.media_y``: where the image's *bottom*
    goes, as a fraction of the stage's height.

    The bottom rather than the top, because a staged figure stands on
    something: its baseline is the part a placement is about. ``None`` keeps
    the shared floor every slotted portrait sits on.
    """

    keep: str | None = None
    """From ``staging_hints.media_keep``: ``whole``, ``width``, ``height`` or
    ``none``.

    Which extents of a *named station* this client may pull inside the frame.
    It never touches a fraction: a placement is exact, including off-stage,
    because holding a number on screen moves it somewhere else while keeping
    the same hint. ``None`` defers to this client's own policy
    (:attr:`Stage.keep_on_screen`); ``"none"`` overrides that policy and asks
    for the station exactly where it falls.
    """

    flip_h: bool = False
    """From ``staging_hints.media_flip_h``. Other staging hints are ignored by
    this port; honouring a subset is expected of a conforming client."""

    clip: str | None = None
    """From ``staging_hints.media_clip``: which clip of a sprite sheet to play.

    ``None`` means the still, even when sheets are available -- playing a clip is
    something a use asks for, not something a client assumes."""

    timing: TimingName | None = None
    """From ``staging_hints.media_timing``, kept as stated.

    This port honours all of it for clips: ``loop`` repeats forever (a sheet cannot
    say "forever"); ``restart`` starts the clip over each time a turn states it;
    ``pause`` holds the frame showing and ``stop`` the first; ``start`` or nothing
    plays the clip as its sheet times it and then holds the last frame."""

    sheets: tuple["SheetSource", ...] = ()
    """Sprite sheets delivered beside the still. The still stays the floor."""


@dataclass(slots=True, frozen=True)
class SheetSource:
    """One sprite sheet a staged image may play instead of its still."""

    source: str
    manifest: SpriteSheetManifest


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
class SurfaceSlot:
    """One place on a surface, and the piece kind that lies there.

    ``holds`` is mechanic vocabulary the client never interprets -- it only
    checks it against :attr:`Piece.kind`. That is the whole join: the world says
    where an id card lies, the mechanic says which pieces are id cards, and
    neither names the other.
    """

    name: str
    holds: str
    x: float
    y: float
    w: float
    h: float


@dataclass(slots=True, frozen=True)
class Surface:
    """A surface pieces rest on: an extent, and named slots measured on it.

    Geometry only, in fractions of whatever rect the client hands the stage.
    Which slots are filled this turn is decided by intersecting ``holds`` against
    the live pieces, never by anything stored here -- so a surface is stable
    reference data that outlives any single turn, exactly like a map plate.
    """

    name: str
    image: str | None = None
    band: tuple[float, float, float, float] | None = None
    slots: tuple[SurfaceSlot, ...] = ()


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

    surface: Surface | None = None
    """Also from story-info, and for the same reason: the furniture changes when
    the block changes, not when the player acts."""


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
class ConfirmSelection:
    """Commit the pieces picked so far. Only offered once the minimum is met.

    A selection whose ``min`` and ``max`` differ has no moment the client can
    infer -- and a ``min=0`` selection has to be submittable while empty -- so
    the player says when they are done.
    """


@dataclass(slots=True, frozen=True)
class PageSelection:
    """Show the next page of candidates. Client-local."""


@dataclass(slots=True, frozen=True)
class PagePanel:
    """Show the next page of the state panel. Client-local."""


@dataclass(slots=True, frozen=True)
class CancelSelection:
    """Abandon the pending selection. Client-local.

    Reachable by click as well as by key: a selection a mouse can enter but only
    a keyboard can leave is not a usable surface.
    """


Action = (
    Commit
    | BeginSelection
    | PickPiece
    | ConfirmSelection
    | PageSelection
    | PagePanel
    | CancelSelection
)


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
    def satisfied(self) -> bool:
        """True once the selection may be committed.

        A ``min=0`` choice is satisfied before anything is picked, which is the
        only way an optional selection can be submitted empty.
        """

        return len(self.picked) >= self.choice.accepts.min

    @property
    def full(self) -> bool:
        """True once no further piece may be added; the client commits here."""

        return len(self.picked) >= self.choice.accepts.max
