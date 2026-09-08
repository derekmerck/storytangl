"""Pygame renderer for one :class:`Turn`.

Draws to a 320x200 logical surface and scales up with nearest-neighbour, so the
output sits on a real pixel grid at any window size.

The renderer keys entirely off ``media_role`` and fragment attribution. It holds
no world-specific knowledge: a world with no art still plays, rendering flat
colour plus text.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pygame

from dataclasses import dataclass

from .bridge import (
    UnsupportedAccepts,
    commit_payload,
    place_pieces,
    remaining_pieces,
)
from .models import (
    Action,
    BeginSelection,
    CancelSelection,
    Choice,
    Commit,
    ConfirmSelection,
    MapPlate,
    MapRegion,
    PagePanel,
    PageSelection,
    PendingSelection,
    Piece,
    PickPiece,
    StageImage,
    Surface,
    SurfaceSlot,
    Turn,
    Zone,
)


@dataclass(slots=True, frozen=True)
class _Row:
    """One rendered text row.

    Paging works over rows rather than whole lines, so a single paragraph
    longer than the surface still renders and remains reachable.
    """

    text: str
    kind: str

REFUSED_PIN = "X"
"""What a map region pins when no key commits it. See :meth:`Stage._pin`."""

LOGICAL_SIZE = (320, 200)
SCALE = 3

BACKGROUND_ROLES = ("narrative_im", "cover_im")
PORTRAIT_ROLES = ("dialog_im", "avatar_im")
MAP_ROLES = ("map_im",)
"""A plate is full-frame but is not scenery: it is deliberately outside
BACKGROUND_ROLES so a client with no map view never stages it as a backdrop."""

PORTRAIT_HEIGHT = 112
MARGIN = 10
_DEFAULT_SLOTS = ("left", "right", "mid")
ROW_H = 9
PROSE_TOP = 24

PANEL_W = 104
"""Width reserved for the state panel when a turn has state worth showing.

Decision Legibility (§5.1) makes rendering pieces a requirement, not a
flourish, so the space is taken from the prose rather than shared with it: a
document that scrolled away is a document the player cannot evaluate.
"""

INK = (26, 28, 44)
CREAM = (232, 226, 205)
TEAL = (63, 96, 99)
RUST = (168, 92, 56)
DIM = (120, 118, 110)
ALERT = (198, 76, 56)

_EMPHASIS_COLOURS = {"ok": TEAL, "warn": RUST, "danger": ALERT, "subtle": DIM}

_ROW_STYLES = {
    "heading": (CREAM, RUST),
    "dialog": (CREAM, INK),
    "narration": (INK, CREAM),
    "alt": (INK, DIM),
    "choice": (INK, CREAM),
}

def choice_action(choice: Choice) -> Action | None:
    """Return the action a row for ``choice`` performs, or None if it cannot.

    Three outcomes, and the third is the interesting one. A ``pick`` resolves
    straight to a commit. A ``pieces`` choice opens a selection first. Anything
    this port cannot collect a value for yields None, so the row renders inert
    with its reason rather than committing a guessed payload or crashing the
    frame -- the CLI refuses the same kinds unless handed an explicit payload.
    """

    if not choice.available:
        return None
    if getattr(choice.accepts, "kind", "pick") == "pieces":
        return BeginSelection(choice=choice)
    try:
        return Commit(edge_id=choice.edge_id, payload=commit_payload(choice))
    except UnsupportedAccepts:
        return None


def unsupported_reason(choice: Choice) -> str | None:
    """Why an available choice still has no action, for the player to read."""

    if not choice.available or choice_action(choice) is not None:
        return None
    return f"needs {getattr(choice.accepts, 'kind', 'unknown')} input"


SELECTION_ROWS = 7
"""Candidates shown at once before the list pages.

Seven, not eight, because the control keys are drawn from the same numeric
keypad the candidates are: ``8`` confirms, ``9`` pages, ``0`` cancels. An eighth
candidate would be clickable but unreachable by key -- and once the minimum was
met, ``8`` would commit instead of picking the row the player is looking at.

A twenty-document packet would otherwise lay its first rows above the top of the
surface, where they are neither readable nor clickable.
"""

CONFIRM_KEY = 8
PAGE_KEY = 9
CANCEL_KEY = 0

SURFACE_CONTOUR = 1
SURFACE_WASH = 140
TEXT_WASH = 210
"""Opacity of a text backing, out of 255.

Opaque backings were readable and hid the scene behind a slab. A wash keeps
the contrast the text needs -- cream on near-black is a long way from the
palette's midtones -- while leaving the art legible underneath, the way a
terminal shows a wallpaper through its window."""
"""How the client paints a surface band: a wash of this alpha plus a lit edge.

A darkened band with a contour along its top reads as a surface projecting away
from the viewer, which is why a desk needs no art. The wash rather than a fill
because a world may already have a desk in its background -- `hall_monitor` does
-- and an opaque rectangle would paint over the very thing it is describing.
Over flat colour the same wash still reads as a distinct band.

The rectangle comes from the world; the colour, wash and contour are the
client's, and a port with a different palette owes nothing here."""

MAP_FOOTER_ROWS = 8
"""Rows the map footer may occupy before it scrolls. A map drawn under a
footer that grows without limit is a map nobody can see."""


class Stage:
    """Own the display surface, fonts, and per-frame hit regions."""

    def __init__(self, asset_dir: Path | None = None, *, title: str = "StoryTangl") -> None:
        pygame.init()
        self.window = pygame.display.set_mode(
            (LOGICAL_SIZE[0] * SCALE, LOGICAL_SIZE[1] * SCALE)
        )
        pygame.display.set_caption(title)
        self.surface = pygame.Surface(LOGICAL_SIZE)
        self.asset_dir = asset_dir
        self.font = pygame.font.Font(None, 11)
        self._cache: dict[str, pygame.Surface | None] = {}
        self.hitboxes: list[tuple[pygame.Rect, Action]] = []
        self.slot_boxes: list[tuple[SurfaceSlot, Piece, pygame.Rect]] = []
        """Where each placed piece was drawn this frame.

        Recorded for the same reason hitboxes are: it is the only honest
        answer to where a piece is, and anything that recomputes it from the
        slot fractions is a second derivation that can drift.
        """
        self.scroll = 0
        self.max_scroll = 0
        self.selection_scroll = 0
        self.panel_scroll = 0
        self.prose_floor = LOGICAL_SIZE[1]
        self.selection_numbers: dict[str, int] = {}
        self._last_turn: Turn | None = None

    # ── assets ───────────────────────────────────────────────────────────

    def _load(self, source: str) -> pygame.Surface | None:
        """Resolve one media source to a surface, or None when unavailable."""

        if source in self._cache:
            return self._cache[source]
        surface: pygame.Surface | None = None
        candidate = Path(source)
        if not candidate.is_absolute() and self.asset_dir is not None:
            candidate = self.asset_dir / source
        if candidate.is_file():
            try:
                surface = pygame.image.load(str(candidate)).convert_alpha()
            except pygame.error:
                surface = None
        self._cache[source] = surface
        return surface

    def _resolve_images(
        self, turn: Turn
    ) -> tuple[list[tuple[StageImage, pygame.Surface]], list[StageImage]]:
        """Split staged images into drawable surfaces and those that are not.

        An accepted source the renderer cannot load — a remote URL, a missing
        or unreadable file — must not vanish. It degrades to its text floor.
        """

        loaded: list[tuple[StageImage, pygame.Surface]] = []
        unloadable: list[StageImage] = []
        for image in turn.images:
            surface = self._load(image.source)
            if surface is None:
                unloadable.append(image)
                continue
            if image.flip_h:
                surface = pygame.transform.flip(surface, True, False)
            loaded.append((image, surface))
        return loaded, unloadable

    @staticmethod
    def _pick(
        loaded: list[tuple[StageImage, pygame.Surface]], roles: tuple[str, ...]
    ) -> list[tuple[StageImage, pygame.Surface]]:
        return [entry for role in roles for entry in loaded if entry[0].role == role]

    # ── drawing ──────────────────────────────────────────────────────────

    def draw(self, turn: Turn, pending: PendingSelection | None = None) -> None:
        """Render one turn and record its hitboxes for the input layer.

        While ``pending`` is set the choice list is replaced by the pieces that
        choice will accept. That is the second half of the two-step click-pick
        path the Input Parity rule requires: the same numbered list, the same
        keys, and the same payload the CLI would build.
        """

        self.hitboxes.clear()
        self.slot_boxes.clear()
        loaded, unloadable = self._resolve_images(turn)
        # A map is a way to travel, not a way to pick a document; while a
        # selection is open the plate would offer edges that are not on offer.
        if pending is None and self._draw_map(turn, loaded):
            pygame.transform.scale(self.surface, self.window.get_size(), self.window)
            pygame.display.flip()
            return
        self._draw_background(loaded)
        # Rows below are laid out first and always reserved, so a long exchange
        # can never push the only way to continue off the logical surface.
        # Placement is pure data -- slots against piece kinds, no pixels -- so it
        # settles first. Everything downstream depends on it: the rows the
        # selection still needs, and therefore where the choice list starts, and
        # therefore the rect the surface itself is measured into.
        placed = place_pieces(turn.surface, turn.pieces) if turn.surface else []
        on_surface = {piece.piece_id for _slot, piece in placed}
        # One numbering, drawn in two places. `_keyed` resolves a number key
        # against `selection_page`, so a card that labelled itself by its own
        # count would agree with the keyboard only until a piece was picked.
        numbers = (
            {}
            if pending is None
            else {
                piece.piece_id: index
                for index, piece in enumerate(self.selection_page(turn, pending), start=1)
            }
        )
        self.selection_numbers = numbers
        below = (
            self._selection_rows(turn, pending, on_surface=on_surface)
            if pending is not None
            else len(turn.choices)
        )
        choices_top = LOGICAL_SIZE[1] - 4 - below * 11
        self._draw_portraits(loaded, floor=choices_top)
        panelled = self._has_state(turn, placed=placed)
        width = LOGICAL_SIZE[0] - (PANEL_W if panelled else 0)
        stage_rect = pygame.Rect(0, PROSE_TOP, width, choices_top - PROSE_TOP)
        # Recorded because it is a seam: the surface decides it and the prose
        # layout consumes it, and a test that re-derives it from row counts
        # instead passes whether or not the two agree.
        self.prose_floor = self._draw_surface(
            turn, placed, rect=stage_rect, pending=pending, numbers=numbers
        )
        prose_floor = self.prose_floor
        rows = self._rows(turn, unloadable, columns=(width - 12) // 4)
        capacity = max(1, (prose_floor - PROSE_TOP) // ROW_H)
        self.max_scroll = max(0, len(rows) - capacity)
        if turn is not self._last_turn:
            self.scroll = self.max_scroll  # newest text first on a fresh turn
            self._last_turn = turn
        self.scroll = min(max(self.scroll, 0), self.max_scroll)
        self._draw_rows(rows[self.scroll : self.scroll + capacity], capacity=capacity, width=width)
        if panelled:
            self._draw_state_panel(turn, top=2, bottom=choices_top, placed=placed)
        if pending is not None:
            self._draw_selection(
                turn, pending, top=choices_top, on_surface=on_surface, numbers=numbers
            )
        else:
            self._draw_choices(turn, top=choices_top)
        pygame.transform.scale(self.surface, self.window.get_size(), self.window)
        pygame.display.flip()

    # ── map view ─────────────────────────────────────────────────────────

    def _draw_map(
        self, turn: Turn, loaded: list[tuple[StageImage, pygame.Surface]]
    ) -> bool:
        """Draw the plate with a hitbox per claimed region. False when no map.

        Numbering runs over the whole choice list, so a region's label and its
        keyboard shortcut are the same number, and a choice no region claims
        still gets an ordinary row. That is the Input Parity floor made visible
        rather than merely asserted in a test.
        """

        plate = turn.plate
        staged = self._pick(loaded, MAP_ROLES)
        if plate is None or not staged:
            return False
        surface = self._plate_surface(plate, staged)
        if surface is None:
            return False

        self.surface.blit(pygame.transform.scale(surface, LOGICAL_SIZE), (0, 0))
        claimed = self._claimed_regions(turn, plate)
        for index, choice, region in claimed:
            self._draw_region(index, choice, region)

        self._draw_map_footer(turn)
        return True

    @staticmethod
    def _plate_surface(
        plate: MapPlate, staged: list[tuple[StageImage, pygame.Surface]]
    ) -> pygame.Surface | None:
        """Pick the image this plate names, never merely the first staged one.

        Geometry and image arrive by different routes, so drawing a map whose
        picture is one place and whose hitboxes are another is a real failure
        mode rather than a hypothetical one. When the plate names no image, a
        single staged map is unambiguous and anything more is not.
        """

        if plate.image:
            for image, surface in staged:
                if Path(image.source).name == plate.image:
                    return surface
            return None
        return staged[0][1] if len(staged) == 1 else None

    @staticmethod
    def _claimed_regions(
        turn: Turn, plate: MapPlate
    ) -> list[tuple[int, Choice, MapRegion]]:
        """Pair each region with the choice claiming it, in plate order.

        A region no choice claims is simply absent from the result: nothing is
        drawn and nothing is clickable, which is how a place that is not on
        offer differs from one that is offered and refused.
        """

        by_tag: dict[str, list[tuple[int, Choice]]] = {}
        for index, choice in enumerate(turn.choices, start=1):
            for tag in choice.tags:
                by_tag.setdefault(tag, []).append((index, choice))
        pairs: list[tuple[int, Choice, MapRegion]] = []
        for region in plate.regions:
            matches = by_tag.get(plate.claim(region)) or []
            if len(matches) != 1:
                # Zero is an inert region. More than one is ambiguous, and the
                # engine already refuses to project it; picking one here would
                # hide a dropped choice behind a hitbox that looks correct.
                continue
            index, choice = matches[0]
            pairs.append((index, choice, region))
        return pairs

    def _draw_region(self, index: int, choice: Choice, region: MapRegion) -> None:
        """Outline one region and pin its choice number inside the corner.

        The pin carries the number only. A 70px box cannot hold "Go to The
        Practice Yard", and the client is not allowed to shorten it — that
        would mean parsing prose it does not own — so the names stay in the
        legend and the number is what ties the two together.

        A refused region pins `x`, because the number would be a key that does
        nothing. See :meth:`_marker`.
        """

        rect = pygame.Rect(
            round(region.x * LOGICAL_SIZE[0]),
            round(region.y * LOGICAL_SIZE[1]),
            max(4, round(region.w * LOGICAL_SIZE[0])),
            max(4, round(region.h * LOGICAL_SIZE[1])),
        )
        # Dim on actionability, not availability: a choice this port cannot
        # collect a value for has no hitbox either, and a live-looking box over
        # dead pixels is exactly the hidden dropped choice the map view refuses
        # elsewhere.
        action = choice_action(choice)
        colour = CREAM if action is not None else DIM
        pygame.draw.rect(self.surface, colour, rect, width=1)

        # `x` rather than a number for a refused region, for the same reason
        # its legend row carries one: the pin is the key, and this box has no
        # key. Dimmed box, `x` pin, `x)` row -- the three still tie together.
        text = self.font.render(self._pin(index, choice), False, colour)
        pin = pygame.Rect(rect.x + 1, rect.y + 1, text.get_width() + 4, ROW_H)
        self._wash(pin, INK)
        self.surface.blit(text, (pin.x + 2, pin.y))

        if action is not None:
            self.hitboxes.append((rect, action))

    def _draw_map_footer(self, turn: Turn) -> None:
        """Narration and the full numbered legend, bounded and pageable.

        Every choice appears here, including ones that already have a box on
        the plate. That is the Input Parity floor kept literally on screen: the
        same number, the same edge, whichever the reader clicks.

        The footer is capped and scrolls rather than growing without limit —
        an attributed exchange on a map location would otherwise cover the map
        it is drawn over. Paging starts at the bottom so the choices, which are
        the only way to continue, are what a fresh turn shows.
        """

        rows = self._rows(turn, [], columns=74)
        rows.extend(
            _Row(self._choice_label(index, choice), "choice")
            for index, choice in enumerate(turn.choices, start=1)
        )
        if not rows:
            return

        capacity = min(len(rows), MAP_FOOTER_ROWS)
        self.max_scroll = max(0, len(rows) - capacity)
        if turn is not self._last_turn:
            self.scroll = self.max_scroll
            self._last_turn = turn
        self.scroll = min(max(self.scroll, 0), self.max_scroll)

        visible = rows[self.scroll : self.scroll + capacity]
        y = LOGICAL_SIZE[1] - capacity * ROW_H - 2
        # Choices are keyed by their number rather than by row order, so a
        # scrolled-away choice stays selectable from the keyboard. Two refused
        # rows with the same text now share a key, since both are labelled
        # `x)`; that is harmless because neither has an action to recover.
        by_label = {
            self._choice_label(index, choice): choice
            for index, choice in enumerate(turn.choices, start=1)
        }
        for row in visible:
            self._wash(pygame.Rect(0, y, LOGICAL_SIZE[0], ROW_H), INK)
            choice = by_label.get(row.text) if row.kind == "choice" else None
            action = choice_action(choice) if choice is not None else None
            colour = CREAM
            if choice is not None and action is None:
                colour = DIM
            elif row.kind == "heading":
                colour = RUST
            # Clipped like an ordinary row: a legend line is one line for the
            # same reason, and the hitbox is sized from what was drawn rather
            # than from what was asked for, so it cannot reach past the frame.
            text = self.font.render(self._clip(row.text), False, colour)
            self.surface.blit(text, (4, y))
            if action is not None:
                rect = pygame.Rect(4, y, text.get_width(), ROW_H)
                self.hitboxes.append((rect, action))
            y += ROW_H

        if self.max_scroll:
            marker = f"{self.scroll + 1}/{self.max_scroll + 1}  \u2191\u2193"
            surface = self.font.render(marker, False, DIM)
            self.surface.blit(
                surface,
                (LOGICAL_SIZE[0] - surface.get_width() - 4,
                 LOGICAL_SIZE[1] - capacity * ROW_H - ROW_H - 2),
            )

    @staticmethod
    def _pin(index: int, choice: Choice) -> str:
        """Return the key that commits this choice, or `X` when it has none.

        One function for both surfaces. The plate's pin and the row's marker
        are the same claim about the same choice, and deriving them separately
        is how a box ends up numbered while its legend row is not.

        Capital, because at 11px the default font renders a lowercase `x` as a
        3x4 blob indistinguishable from a filled square, while `X` keeps its
        crossbars. The legend keeps `x)`, where the bracket carries the shape
        and the pair matches what the CLI prints.
        """

        return REFUSED_PIN if choice_action(choice) is None else str(index)

    @staticmethod
    def _marker(index: int, choice: Choice) -> str:
        """Return what goes in front of a row: its key, or that it has none.

        Numbering is positional, so the number a row shows is the key that
        commits it. A row this port cannot commit has no key, and printing its
        position invites a press that silently does nothing — so it prints
        `x)` instead. Live rows therefore run 1, 3, 6 rather than 1, 2, 3: the
        gaps are the refusals, and every number on screen works.

        Whether the ports should agree on *which* number names a given edge is
        a separate and open question (#452) — the CLI numbers only the live
        rows, so the same edge can be 2 there and 3 here.
        """

        pin = Stage._pin(index, choice)
        return "x)" if pin == REFUSED_PIN else f"{pin}."

    @staticmethod
    def _choice_label(index: int, choice: Choice) -> str:
        label = f"{Stage._marker(index, choice)} {choice.text}"
        # An available choice this port cannot collect a value for still needs
        # to say why, or its dimmed legend row reads as an engine refusal.
        if reason := (choice.unavailable_reason or unsupported_reason(choice)):
            return f"{label} — {reason}"
        return label

    # ── surface ──────────────────────────────────────────────────────────

    def _draw_surface(
        self,
        turn: Turn,
        placed: list[tuple[SurfaceSlot, Piece]],
        *,
        rect: pygame.Rect,
        pending: PendingSelection | None,
        numbers: dict[str, int],
    ) -> int:
        """Draw the surface and the pieces resting on it. Returns the prose floor.

        The world declares fractions; ``rect`` is the client's own stage area,
        already narrowed for the state panel. That is what normalized geometry is
        for -- the world never learns this client's pixels, and a second desk
        with different coordinates needs nothing here.

        Prose stops above everything the surface draws, not merely above the band,
        and that is the whole point of moving the packet onto a desk: the lower
        stage is the desk, and the desk is what the player is looking at. Taking
        the floor from the band alone would let a slot standing behind the desk
        be painted over by the very text it was making room for.
        """

        surface = turn.surface
        if surface is None:
            return rect.bottom

        floor = rect.bottom
        if surface.band is not None:
            band = self._rect_in(rect, *surface.band)
            wash = pygame.Surface(band.size, pygame.SRCALPHA)
            wash.fill((*INK, SURFACE_WASH))
            self.surface.blit(wash, band.topleft)
            pygame.draw.rect(
                self.surface, CREAM, pygame.Rect(band.x, band.y, band.w, SURFACE_CONTOUR)
            )
            floor = band.top
        for slot, _piece in placed:
            floor = min(floor, self._rect_in(rect, slot.x, slot.y, slot.w, slot.h).top)

        # The page, not every remaining candidate. `numbers` is built from
        # `selection_page`, so taking clickability from anywhere else lets a card
        # on another page be picked by mouse while carrying no number and being
        # unreachable by key -- the same drift the numbering was already
        # centralized to avoid, one step further along.
        offered = set(numbers)

        # Nearer the viewer is drawn later. Depth comes off the slot's own
        # baseline rather than a separate declaration, so the two can never
        # disagree about which piece is in front.
        for slot, piece in sorted(placed, key=lambda pair: pair[0].y + pair[0].h):
            self._draw_piece(
                slot,
                piece,
                rect=rect,
                pickable=piece.piece_id in offered,
                picked=pending is not None and piece.piece_id in pending.picked,
                number=numbers.get(piece.piece_id),
            )
        return floor

    def _draw_piece(
        self,
        slot: SurfaceSlot,
        piece: Piece,
        *,
        rect: pygame.Rect,
        pickable: bool,
        picked: bool,
        number: int | None = None,
    ) -> None:
        """Draw one piece in its slot, and make it clickable when it is on offer.

        A piece is drawn whenever it is on the surface and clickable only while a
        selection wants it. Nothing here can commit: a click yields ``PickPiece``,
        exactly what the key yields.

        The card carries ``number`` when one is on offer, and that is what buys
        the room: §5.3 Input Parity wants every click reachable by keyboard, not
        a second list saying so. A card the player can see, click and type the
        number of satisfies it outright, so the row it would have occupied is
        given back to the desk.
        """

        box = self._rect_in(rect, slot.x, slot.y, slot.w, slot.h)
        self.slot_boxes.append((slot, piece, box))
        edge = RUST if picked else (CREAM if piece.available else DIM)
        pygame.draw.rect(self.surface, CREAM if piece.available else INK, box)
        pygame.draw.rect(self.surface, edge, box, 1)

        label = piece.label or piece.piece_id
        if number is not None:
            label = f"{number}. {label}"
        elif not piece.available:
            # The same mark an inactive choice row carries. It says the card is
            # not on offer; the panel row still says why.
            label = f"(x) {label}"
        for index, line in enumerate(self._wrap(label, max(1, (box.w - 4) // 4))):
            y = box.y + 3 + index * ROW_H
            if y + ROW_H > box.bottom:
                break
            self.surface.blit(
                self.font.render(line, False, INK if piece.available else DIM),
                (box.x + 3, y),
            )
        if pickable:
            self.hitboxes.append((box, PickPiece(piece_id=piece.piece_id)))

    @staticmethod
    def _rect_in(rect: pygame.Rect, x: float, y: float, w: float, h: float) -> pygame.Rect:
        """Map one normalized rectangle into a pixel rect."""

        return pygame.Rect(
            rect.x + round(x * rect.w),
            rect.y + round(y * rect.h),
            max(1, round(w * rect.w)),
            max(1, round(h * rect.h)),
        )

    def _draw_background(
        self, loaded: list[tuple[StageImage, pygame.Surface]]
    ) -> None:
        backgrounds = self._pick(loaded, BACKGROUND_ROLES)
        if backgrounds:
            surface = backgrounds[0][1]
            self.surface.blit(pygame.transform.scale(surface, LOGICAL_SIZE), (0, 0))
        else:
            self.surface.fill(TEAL)

    def _draw_portraits(
        self, loaded: list[tuple[StageImage, pygame.Surface]], *, floor: int
    ) -> None:
        """Place up to two sprites on a shared baseline, preserving aspect."""

        staged = self._pick(loaded, PORTRAIT_ROLES)[:3]
        for index, (image, portrait) in enumerate(staged):
            height = min(PORTRAIT_HEIGHT, max(24, floor - 24))
            width = max(1, round(portrait.get_width() * height / portrait.get_height()))
            scaled = pygame.transform.scale(portrait, (width, height))
            slot = image.x_slot or _DEFAULT_SLOTS[min(index, len(_DEFAULT_SLOTS) - 1)]
            self.surface.blit(scaled, (self._slot_x(slot, width), floor - height))

    @staticmethod
    def _slot_x(slot: str, width: int) -> int:
        """Left edge for a horizontal staging slot. Unknown slots centre."""

        if slot == "left":
            return MARGIN
        if slot == "right":
            return LOGICAL_SIZE[0] - width - MARGIN
        return (LOGICAL_SIZE[0] - width) // 2

    def _rows(
        self, turn: Turn, unloadable: list[StageImage], *, columns: int = 74
    ) -> list[_Row]:
        """Flatten a turn into rendered rows, including media text floors."""

        rows: list[_Row] = []
        for line in turn.lines:
            if line.speaker is not None:
                heading = f"{line.speaker} ({line.manner})" if line.manner else line.speaker
                rows.append(_Row(heading, "heading"))
                rows.extend(_Row(part, "dialog") for part in self._wrap(line.text, columns))
            else:
                rows.extend(_Row(part, "narration") for part in self._wrap(line.text, columns))
        for image in unloadable:
            text = image.alt_text or f"[{image.role} unavailable]"
            rows.extend(_Row(part, "alt") for part in self._wrap(text, columns))
        return rows

    def _wash(self, rect: pygame.Rect, colour: tuple[int, int, int]) -> None:
        """Lay a translucent backing under text.

        One function for every backing in the client, so a prose row, a choice
        row, the state column and a map pin cannot drift to different
        opacities and read as different surfaces.
        """

        wash = pygame.Surface(rect.size, pygame.SRCALPHA)
        wash.fill((*colour, TEXT_WASH))
        self.surface.blit(wash, rect.topleft)

    def _draw_rows(self, rows: list[_Row], *, capacity: int, width: int) -> None:
        """Draw one page of rows, bottom-aligned, with a scroll indicator."""

        y = PROSE_TOP + max(0, capacity - len(rows)) * ROW_H
        for row in rows:
            fill, colour = _ROW_STYLES[row.kind]
            self._wash(pygame.Rect(6, y, width - 12, ROW_H), fill)
            self.surface.blit(self.font.render(row.text, False, colour), (9, y))
            y += ROW_H
        if self.max_scroll:
            marker = f"{self.scroll + 1}/{self.max_scroll + 1}  \u2191\u2193"
            surface = self.font.render(marker, False, DIM)
            self.surface.blit(surface, (LOGICAL_SIZE[0] - surface.get_width() - 8, PROSE_TOP - 10))

    def scroll_by(self, delta: int) -> None:
        """Page through prose. Clamped; a no-op when everything already fits."""

        self.scroll = min(max(self.scroll + delta, 0), self.max_scroll)

    def _row(self, marker: str, text: str, *, y: int, colour, action: Action | None) -> None:
        """Draw one numbered row and, when actionable, record its hitbox.

        Rows sit directly on the scene, so they carry their own backing. Prose
        has had one since the beginning; choices did not, and cream text over a
        pale plate -- a sunlit market, a parchment floor -- was unreadable
        exactly where the art was working hardest.
        """

        surface = self.font.render(self._clip(f"{marker} {text}"), False, colour)
        rect = pygame.Rect(8, y, surface.get_width(), surface.get_height())
        backing = rect.inflate(6, 2)
        backing.left = 5
        self._wash(backing, INK)
        self.surface.blit(surface, rect.topleft)
        if action is not None:
            self.hitboxes.append((rect, action))

    def _draw_choices(self, turn: Turn, *, top: int) -> None:
        y = top
        for index, choice in enumerate(turn.choices, start=1):
            action = choice_action(choice)
            label = choice.text
            if reason := (choice.unavailable_reason or unsupported_reason(choice)):
                label = f"{label}  — {reason}"
            self._row(
                self._marker(index, choice),
                label,
                y=y,
                colour=CREAM if action is not None else DIM,
                action=action,
            )
            y += 11

    @staticmethod
    def _shown(placed: list[tuple[SurfaceSlot, Piece]]) -> set[str]:
        """Pieces the desk represents completely enough to drop from the panel.

        An unavailable piece is not one of them. The card can say *that* it is
        spent -- dimmed, marked, carrying no number -- but a card is about forty
        pixels wide and cannot say *why*, and the reason is the whole point:
        widget vocabulary §7.1 wants a blocked member to announce itself rather
        than let the player discover it from the error after committing. So it
        stays in the column, where its reason has room.
        """

        return {piece.piece_id for _slot, piece in placed if piece.available}

    @staticmethod
    def _panel_zones(turn: Turn, shown: set[str]) -> list[Zone]:
        """Zones the panel still owes the player a heading for.

        A zone whose every member is laid out on the desk is redundant. An
        *empty* zone is not: a targetable container with nothing in it is
        information, not an absence, and that holds whether or not there is a
        surface. Written once because ``_has_state`` and ``panel_rows`` have to
        agree -- a panel that decides to draw and then finds nothing to say is
        a quarter of the width spent on a blank column.
        """

        zones: list[Zone] = []
        for zone in turn.zones:
            members = [piece for piece in turn.pieces if piece.zone_ref == zone.uid]
            if not members or any(piece.piece_id not in shown for piece in members):
                zones.append(zone)
        return zones

    @classmethod
    def _has_state(
        cls, turn: Turn, *, placed: list[tuple[SurfaceSlot, Piece]] = []
    ) -> bool:
        """True when there is state the surface did not already show.

        A packet entirely laid out on a desk needs no column repeating it, and on
        a 320x200 stage that column is a quarter of the width. What the surface
        could not place still earns one.
        """

        shown = cls._shown(placed)
        return bool(
            [piece for piece in turn.pieces if piece.piece_id not in shown]
            or turn.findings
            or cls._panel_zones(turn, shown)
        )

    def panel_rows(
        self,
        turn: Turn,
        *,
        columns: int,
        placed: list[tuple[SurfaceSlot, Piece]] = [],
    ) -> list[tuple[str, tuple[int, int, int]]]:
        """Flatten the state panel into wrapped, coloured rows.

        Built as data so it can be paged. An overflow notice admitted state was
        missing without offering any way to read it, which is not what §5.1
        asks for.
        """

        rows: list[tuple[str, tuple[int, int, int]]] = []
        # Whatever the surface drew, the player is already looking at. The panel
        # is for the remainder -- a piece whose kind no slot holds, or a whole
        # packet on a world that declares no surface at all.
        shown = self._shown(placed)

        def wrapped(text: str, colour, *, indent: str = "") -> None:
            for part in self._wrap(text, columns - len(indent)):
                rows.append((f"{indent}{part}", colour))

        # Pieces outside any zone first -- in a credentials shift that is the
        # traveler, and who you are judging outranks what they handed over.
        for piece in turn.pieces:
            if piece.zone_ref is None and piece.piece_id not in shown:
                wrapped(piece.label or piece.piece_id, CREAM)

        for zone in self._panel_zones(turn, shown):
            members = [
                piece
                for piece in turn.pieces
                if piece.zone_ref == zone.uid and piece.piece_id not in shown
            ]
            wrapped((zone.label or zone.role or "zone").upper(), RUST)
            for piece in members:
                name = piece.label or piece.piece_id
                if not piece.available and piece.unavailable_reason:
                    name = f"{name} - {piece.unavailable_reason}"
                wrapped(name, CREAM if piece.available else DIM, indent=" ")
            if not members:
                rows.append((" (empty)", DIM))

        if turn.findings:
            wrapped("FINDINGS", RUST)
            for finding in turn.findings:
                colour = _EMPHASIS_COLOURS.get(finding.emphasis or "", CREAM)
                wrapped(f"{finding.key}: {finding.value}", colour, indent=" ")

        return rows

    def panel_page(
        self,
        rows: list[tuple[str, tuple[int, int, int]]],
        *,
        capacity: int,
    ) -> tuple[int, int, list[tuple[str, tuple[int, int, int]]]]:
        """Split panel rows into the page currently on screen.

        Returned rather than computed inline so a test can assert what is
        *visible*, not merely what the panel knows about. Asserting against the
        full row model passes whether or not paging works at all.
        """

        if len(rows) <= capacity:
            return 0, 1, rows
        capacity -= 1  # the pager occupies the last line
        capacity = max(capacity, 1)
        pages = max(1, -(-len(rows) // capacity))
        page = self.panel_scroll % pages
        return page, pages, rows[page * capacity : page * capacity + capacity]

    def _draw_state_panel(
        self,
        turn: Turn,
        *,
        top: int,
        bottom: int,
        placed: list[tuple[SurfaceSlot, Piece]] = [],
    ) -> None:
        """Draw the pieces, zones and findings a choice may reference.

        This is the §5.1 floor made literal: if the player can pick it, the
        player can see it. Zones render even when empty -- a targetable
        container with nothing in it is information, not an absence -- and
        findings keep the engine's own ``emphasis`` word rather than the client
        re-deriving severity from prose.

        When the state outruns the column it pages, so everything stays
        reachable rather than merely acknowledged.
        """

        left = LOGICAL_SIZE[0] - PANEL_W
        self._wash(pygame.Rect(left, top, PANEL_W, bottom - top), INK)
        columns = (PANEL_W - 10) // 4
        rows = self.panel_rows(turn, columns=columns, placed=placed)
        capacity = max(1, (bottom - top - 4) // ROW_H)

        page, pages, visible = self.panel_page(rows, capacity=capacity)

        y = top + 2
        for text, colour in visible:
            self.surface.blit(self.font.render(text, False, colour), (left + 4, y))
            y += ROW_H

        if pages > 1:
            label = f"page {page + 1}/{pages}  tab"
            surface = self.font.render(label, False, ALERT)
            rect = pygame.Rect(left + 4, bottom - ROW_H, surface.get_width(), ROW_H)
            self.surface.blit(surface, rect.topleft)
            self.hitboxes.append((rect, PagePanel()))

    def selection_page(self, turn: Turn, pending: PendingSelection) -> list:
        """The candidates visible on the current page, in stream order.

        Numbering restarts at 1 per page on purpose: this is the same
        numbered-list input mode the CLI uses for its positional values, so the
        number a player reads is the key they press, whichever page they are on.
        """

        candidates = remaining_pieces(turn, pending)
        start = self.selection_index(turn, pending) * SELECTION_ROWS
        return candidates[start : start + SELECTION_ROWS]

    def selection_index(self, turn: Turn, pending: PendingSelection) -> int:
        """The normalized page number, wrapping cleanly on repeated paging.

        The slice and the label must agree. Wrapping the label with modulo while
        clamping the slice separately made repeated paging over twenty
        candidates walk 0, 8, 16 and then stick at 0 while the label kept
        counting -- and the set shrinks as pieces are picked, so the page count
        moves under the reader.
        """

        return self.selection_scroll % self.selection_pages(turn, pending)

    def selection_pages(self, turn: Turn, pending: PendingSelection) -> int:
        candidates = remaining_pieces(turn, pending)
        return max(1, -(-len(candidates) // SELECTION_ROWS))

    def _selection_rows(
        self,
        turn: Turn,
        pending: PendingSelection,
        *,
        on_surface: set[str] = frozenset(),
    ) -> int:
        """How many rows the selection surface needs, paging included.

        A piece already drawn on the desk, wearing its number, needs no row --
        which is the whole saving. The controls are never on the desk and are
        always counted.
        """

        # Cancel, plus the confirm-or-hint row that is drawn either way. Counting
        # confirm only when satisfied pushed Cancel off the bottom of the surface
        # for an unsatisfied selection.
        extra = 2
        if self.selection_pages(turn, pending) > 1:
            extra += 1
        listed = [
            piece
            for piece in self.selection_page(turn, pending)
            if piece.piece_id not in on_surface
        ]
        return len(listed) + extra

    def _draw_selection(
        self,
        turn: Turn,
        pending: PendingSelection,
        *,
        top: int,
        on_surface: set[str] = frozenset(),
        numbers: dict[str, int] | None = None,
    ) -> None:
        """Draw the pieces a pending choice will accept, plus its controls.

        Pieces the desk is already showing are skipped: they carry the same
        number on their card. The numbers themselves are handed in rather than
        counted here, so the row, the card and the key never disagree about
        which piece is number two.
        """

        y = top
        page = self.selection_page(turn, pending)
        numbering = numbers or {
            piece.piece_id: index for index, piece in enumerate(page, start=1)
        }
        for piece in page:
            if piece.piece_id in on_surface:
                continue
            self._row(
                f"{numbering[piece.piece_id]}.",
                piece.label or piece.piece_id,
                y=y,
                colour=CREAM,
                action=PickPiece(piece_id=piece.piece_id),
            )
            y += 11

        pages = self.selection_pages(turn, pending)
        if pages > 1:
            page = self.selection_index(turn, pending) + 1
            self._row(
                f"{PAGE_KEY}.",
                f"More ({page}/{pages})",
                y=y,
                colour=CREAM,
                action=PageSelection(),
            )
            y += 11

        if pending.satisfied:
            # Only reachable once the minimum is met, and reachable by click as
            # well as by key -- a selection a mouse can enter but only a
            # keyboard can finish is not a usable surface.
            picked = len(pending.picked)
            self._row(
                f"{CONFIRM_KEY}.",
                f"Confirm ({picked} selected)",
                y=y,
                colour=CREAM,
                action=ConfirmSelection(),
            )
            y += 11
        else:
            # Keeps its number where a refused choice would print `x)`: this is
            # a control with a fixed binding, and the number is what the panel
            # is teaching. It starts working the moment the minimum is met.
            self._row(
                f"{CONFIRM_KEY}.",
                f"Pick {pending.wanted} more",
                y=y,
                colour=DIM,
                action=None,
            )
            y += 11

        self._row(f"{CANCEL_KEY}.", "Cancel", y=y, colour=DIM, action=CancelSelection())

    def hit(self, position: tuple[int, int]) -> Action | None:
        """Map a window click to the action its row performs."""

        logical = (position[0] // SCALE, position[1] // SCALE)
        # Reverse draw order: the footer is drawn over the plate, so a legend
        # row sitting on top of a region must win the click it visibly owns.
        for rect, action in reversed(self.hitboxes):
            if rect.collidepoint(logical):
                return action
        return None

    def _clip(self, text: str) -> str:
        """Return `text` shortened until the row fits the frame.

        A choice row is one line by construction — the number a reader presses
        has to stay with the words it names — so a long one cannot wrap and
        used to run off the right edge instead, taking the end of the sentence
        with it silently. Trimming to an ellipsis at least says that there was
        more. Measured rather than counted: the font is proportional, so a
        column budget would clip the wrong worlds.
        """

        limit = LOGICAL_SIZE[0] - 12
        if self.font.size(text)[0] <= limit:
            return text
        clipped = text
        while clipped and self.font.size(f"{clipped}…")[0] > limit:
            clipped = clipped[:-1]
        return f"{clipped.rstrip()}…"

    @staticmethod
    def _wrap(text: str, width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) > width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines or [""]
