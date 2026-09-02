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

from .models import Choice, MapPlate, MapRegion, StageImage, Turn


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

INK = (26, 28, 44)
CREAM = (232, 226, 205)
TEAL = (63, 96, 99)
RUST = (168, 92, 56)
DIM = (120, 118, 110)

_ROW_STYLES = {
    "heading": (CREAM, RUST),
    "dialog": (CREAM, INK),
    "narration": (INK, CREAM),
    "alt": (INK, DIM),
}


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
        self.hitboxes: list[tuple[pygame.Rect, UUID, object]] = []
        self.scroll = 0
        self.max_scroll = 0
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

    def draw(self, turn: Turn) -> None:
        """Render one turn and record choice hitboxes for the input layer."""

        self.hitboxes.clear()
        loaded, unloadable = self._resolve_images(turn)
        if self._draw_map(turn, loaded):
            pygame.transform.scale(self.surface, self.window.get_size(), self.window)
            pygame.display.flip()
            return
        self._draw_background(loaded)
        # Choices are laid out first and always reserved, so a long exchange can
        # never push the only way to continue off the logical surface.
        choices_top = LOGICAL_SIZE[1] - 4 - len(turn.choices) * 11
        self._draw_portraits(loaded, floor=choices_top)

        rows = self._rows(turn, unloadable)
        capacity = max(1, (choices_top - PROSE_TOP) // ROW_H)
        self.max_scroll = max(0, len(rows) - capacity)
        if turn is not self._last_turn:
            self.scroll = self.max_scroll  # newest text first on a fresh turn
            self._last_turn = turn
        self.scroll = min(max(self.scroll, 0), self.max_scroll)
        self._draw_rows(rows[self.scroll : self.scroll + capacity], capacity=capacity)
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

        self.surface.blit(pygame.transform.scale(staged[0][1], LOGICAL_SIZE), (0, 0))
        claimed = self._claimed_regions(turn, plate)
        for index, choice, region in claimed:
            self._draw_region(index, choice, region)

        self._draw_map_footer(turn)
        return True

    @staticmethod
    def _claimed_regions(
        turn: Turn, plate: MapPlate
    ) -> list[tuple[int, Choice, MapRegion]]:
        """Pair each region with the choice claiming it, in plate order.

        A region no choice claims is simply absent from the result: nothing is
        drawn and nothing is clickable, which is how a place that is not on
        offer differs from one that is offered and refused.
        """

        by_tag = {
            tag: (index, choice)
            for index, choice in enumerate(turn.choices, start=1)
            for tag in choice.tags
        }
        pairs: list[tuple[int, Choice, MapRegion]] = []
        for region in plate.regions:
            match = by_tag.get(plate.claim(region))
            if match is not None:
                pairs.append((match[0], match[1], region))
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
        colour = CREAM if choice.available else DIM
        pygame.draw.rect(self.surface, colour, rect, width=1)

        text = self.font.render(str(index), False, colour)
        pin = pygame.Rect(rect.x + 1, rect.y + 1, text.get_width() + 4, ROW_H)
        pygame.draw.rect(self.surface, INK, pin)
        self.surface.blit(text, (pin.x + 2, pin.y))

        if choice.available:
            self.hitboxes.append((rect, choice.edge_id, choice.payload))

    def _draw_map_footer(self, turn: Turn) -> None:
        """Narration and the full numbered legend along the bottom.

        Every choice appears here, including the ones that already have a box
        on the plate. That is the Input Parity floor kept literally on screen:
        the same number, the same edge, whichever the reader clicks.
        """

        rows = [part for line in turn.lines for part in self._wrap(line.text, 74)]
        height = (len(rows) + len(turn.choices)) * ROW_H
        if not height:
            return
        y = LOGICAL_SIZE[1] - height - 2
        for row in rows:
            pygame.draw.rect(self.surface, INK, pygame.Rect(0, y, LOGICAL_SIZE[0], ROW_H))
            self.surface.blit(self.font.render(row, False, CREAM), (4, y))
            y += ROW_H
        for index, choice in enumerate(turn.choices, start=1):
            colour = CREAM if choice.available else DIM
            label = f"{index}. {choice.text}"
            if not choice.available and choice.unavailable_reason:
                label = f"{label} — {choice.unavailable_reason}"
            text = self.font.render(label, False, colour)
            pygame.draw.rect(self.surface, INK, pygame.Rect(0, y, LOGICAL_SIZE[0], ROW_H))
            self.surface.blit(text, (4, y))
            if choice.available:
                rect = pygame.Rect(4, y, text.get_width(), ROW_H)
                self.hitboxes.append((rect, choice.edge_id, choice.payload))
            y += ROW_H

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

    def _rows(self, turn: Turn, unloadable: list[StageImage]) -> list[_Row]:
        """Flatten a turn into rendered rows, including media text floors."""

        rows: list[_Row] = []
        for line in turn.lines:
            if line.speaker is not None:
                heading = f"{line.speaker} ({line.manner})" if line.manner else line.speaker
                rows.append(_Row(heading, "heading"))
                rows.extend(_Row(part, "dialog") for part in self._wrap(line.text, 74))
            else:
                rows.extend(_Row(part, "narration") for part in self._wrap(line.text, 74))
        for image in unloadable:
            text = image.alt_text or f"[{image.role} unavailable]"
            rows.extend(_Row(part, "alt") for part in self._wrap(text, 74))
        return rows

    def _draw_rows(self, rows: list[_Row], *, capacity: int) -> None:
        """Draw one page of rows, bottom-aligned, with a scroll indicator."""

        y = PROSE_TOP + max(0, capacity - len(rows)) * ROW_H
        for row in rows:
            fill, colour = _ROW_STYLES[row.kind]
            pygame.draw.rect(self.surface, fill, pygame.Rect(6, y, LOGICAL_SIZE[0] - 12, ROW_H))
            self.surface.blit(self.font.render(row.text, False, colour), (9, y))
            y += ROW_H
        if self.max_scroll:
            marker = f"{self.scroll + 1}/{self.max_scroll + 1}  \u2191\u2193"
            surface = self.font.render(marker, False, DIM)
            self.surface.blit(surface, (LOGICAL_SIZE[0] - surface.get_width() - 8, PROSE_TOP - 10))

    def scroll_by(self, delta: int) -> None:
        """Page through prose. Clamped; a no-op when everything already fits."""

        self.scroll = min(max(self.scroll + delta, 0), self.max_scroll)

    def _draw_choices(self, turn: Turn, *, top: int) -> None:
        y = top
        for index, choice in enumerate(turn.choices, start=1):
            label = f"{index}. {choice.text}"
            if not choice.available and choice.unavailable_reason:
                label = f"{label}  — {choice.unavailable_reason}"
            colour = CREAM if choice.available else DIM
            surface = self.font.render(label, False, colour)
            rect = pygame.Rect(8, y, surface.get_width(), surface.get_height())
            self.surface.blit(surface, rect.topleft)
            if choice.available:
                self.hitboxes.append((rect, choice.edge_id, choice.payload))
            y += 11

    def hit(self, position: tuple[int, int]) -> tuple[UUID, object] | None:
        """Map a window click to the edge id its choice commits."""

        logical = (position[0] // SCALE, position[1] // SCALE)
        for rect, edge_id, payload in self.hitboxes:
            if rect.collidepoint(logical):
                return edge_id, payload
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
