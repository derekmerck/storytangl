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

from .bridge import UnsupportedAccepts, commit_payload, remaining_pieces
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
    PickPiece,
    StageImage,
    Turn,
)


@dataclass(slots=True, frozen=True)
class _Row:
    """One rendered text row.

    Paging works over rows rather than whole lines, so a single paragraph
    longer than the surface still renders and remains reachable.
    """

    text: str
    kind: str

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
        self.scroll = 0
        self.max_scroll = 0
        self.selection_scroll = 0
        self.panel_scroll = 0
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
        below = (
            self._selection_rows(turn, pending)
            if pending is not None
            else len(turn.choices)
        )
        choices_top = LOGICAL_SIZE[1] - 4 - below * 11
        self._draw_portraits(loaded, floor=choices_top)

        panelled = self._has_state(turn)
        width = LOGICAL_SIZE[0] - (PANEL_W if panelled else 0)
        rows = self._rows(turn, unloadable, columns=(width - 12) // 4)
        capacity = max(1, (choices_top - PROSE_TOP) // ROW_H)
        self.max_scroll = max(0, len(rows) - capacity)
        if turn is not self._last_turn:
            self.scroll = self.max_scroll  # newest text first on a fresh turn
            self._last_turn = turn
        self.scroll = min(max(self.scroll, 0), self.max_scroll)
        self._draw_rows(rows[self.scroll : self.scroll + capacity], capacity=capacity, width=width)
        if panelled:
            self._draw_state_panel(turn, top=2, bottom=choices_top)
        if pending is not None:
            self._draw_selection(turn, pending, top=choices_top)
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

        text = self.font.render(str(index), False, colour)
        pin = pygame.Rect(rect.x + 1, rect.y + 1, text.get_width() + 4, ROW_H)
        pygame.draw.rect(self.surface, INK, pin)
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
        # scrolled-away choice stays selectable from the keyboard.
        by_label = {
            self._choice_label(index, choice): choice
            for index, choice in enumerate(turn.choices, start=1)
        }
        for row in visible:
            pygame.draw.rect(self.surface, INK, pygame.Rect(0, y, LOGICAL_SIZE[0], ROW_H))
            choice = by_label.get(row.text) if row.kind == "choice" else None
            action = choice_action(choice) if choice is not None else None
            colour = CREAM
            if choice is not None and action is None:
                colour = DIM
            elif row.kind == "heading":
                colour = RUST
            text = self.font.render(row.text, False, colour)
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
    def _choice_label(index: int, choice: Choice) -> str:
        label = f"{index}. {choice.text}"
        # An available choice this port cannot collect a value for still needs
        # to say why, or its dimmed legend row reads as an engine refusal.
        if reason := (choice.unavailable_reason or unsupported_reason(choice)):
            return f"{label} — {reason}"
        return label

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

    def _draw_rows(self, rows: list[_Row], *, capacity: int, width: int) -> None:
        """Draw one page of rows, bottom-aligned, with a scroll indicator."""

        y = PROSE_TOP + max(0, capacity - len(rows)) * ROW_H
        for row in rows:
            fill, colour = _ROW_STYLES[row.kind]
            pygame.draw.rect(self.surface, fill, pygame.Rect(6, y, width - 12, ROW_H))
            self.surface.blit(self.font.render(row.text, False, colour), (9, y))
            y += ROW_H
        if self.max_scroll:
            marker = f"{self.scroll + 1}/{self.max_scroll + 1}  \u2191\u2193"
            surface = self.font.render(marker, False, DIM)
            self.surface.blit(surface, (LOGICAL_SIZE[0] - surface.get_width() - 8, PROSE_TOP - 10))

    def scroll_by(self, delta: int) -> None:
        """Page through prose. Clamped; a no-op when everything already fits."""

        self.scroll = min(max(self.scroll + delta, 0), self.max_scroll)

    def _row(self, index: int, text: str, *, y: int, colour, action: Action | None) -> None:
        """Draw one numbered row and, when actionable, record its hitbox.

        Rows sit directly on the scene, so they carry their own backing. Prose
        has had one since the beginning; choices did not, and cream text over a
        pale plate -- a sunlit market, a parchment floor -- was unreadable
        exactly where the art was working hardest.
        """

        surface = self.font.render(f"{index}. {text}", False, colour)
        rect = pygame.Rect(8, y, surface.get_width(), surface.get_height())
        backing = rect.inflate(6, 2)
        backing.left = 5
        pygame.draw.rect(self.surface, INK, backing)
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
                index,
                label,
                y=y,
                colour=CREAM if action is not None else DIM,
                action=action,
            )
            y += 11

    @staticmethod
    def _has_state(turn: Turn) -> bool:
        return bool(turn.pieces or turn.zones or turn.findings)

    def panel_rows(self, turn: Turn, *, columns: int) -> list[tuple[str, tuple[int, int, int]]]:
        """Flatten the state panel into wrapped, coloured rows.

        Built as data so it can be paged. An overflow notice admitted state was
        missing without offering any way to read it, which is not what §5.1
        asks for.
        """

        rows: list[tuple[str, tuple[int, int, int]]] = []

        def wrapped(text: str, colour, *, indent: str = "") -> None:
            for part in self._wrap(text, columns - len(indent)):
                rows.append((f"{indent}{part}", colour))

        # Pieces outside any zone first -- in a credentials shift that is the
        # traveler, and who you are judging outranks what they handed over.
        for piece in turn.pieces:
            if piece.zone_ref is None:
                wrapped(piece.label or piece.piece_id, CREAM)

        for zone in turn.zones:
            wrapped((zone.label or zone.role or "zone").upper(), RUST)
            members = [piece for piece in turn.pieces if piece.zone_ref == zone.uid]
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

    def _draw_state_panel(self, turn: Turn, *, top: int, bottom: int) -> None:
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
        pygame.draw.rect(self.surface, INK, pygame.Rect(left, top, PANEL_W, bottom - top))
        columns = (PANEL_W - 10) // 4
        rows = self.panel_rows(turn, columns=columns)
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

    def _selection_rows(self, turn: Turn, pending: PendingSelection) -> int:
        """How many rows the selection surface needs, paging included."""

        # Cancel, plus the confirm-or-hint row that is drawn either way. Counting
        # confirm only when satisfied pushed Cancel off the bottom of the surface
        # for an unsatisfied selection.
        extra = 2
        if self.selection_pages(turn, pending) > 1:
            extra += 1
        return len(self.selection_page(turn, pending)) + extra

    def _draw_selection(self, turn: Turn, pending: PendingSelection, *, top: int) -> None:
        """Draw the pieces a pending choice will accept, plus its controls."""

        y = top
        for index, piece in enumerate(self.selection_page(turn, pending), start=1):
            self._row(
                index,
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
                PAGE_KEY,
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
                CONFIRM_KEY,
                f"Confirm ({picked} selected)",
                y=y,
                colour=CREAM,
                action=ConfirmSelection(),
            )
            y += 11
        else:
            self._row(
                CONFIRM_KEY,
                f"Pick {pending.wanted} more",
                y=y,
                colour=DIM,
                action=None,
            )
            y += 11

        self._row(CANCEL_KEY, "Cancel", y=y, colour=DIM, action=CancelSelection())

    def hit(self, position: tuple[int, int]) -> Action | None:
        """Map a window click to the action its row performs."""

        logical = (position[0] // SCALE, position[1] // SCALE)
        # Reverse draw order: the footer is drawn over the plate, so a legend
        # row sitting on top of a region must win the click it visibly owns.
        for rect, action in reversed(self.hitboxes):
            if rect.collidepoint(logical):
                return action
        return None

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
