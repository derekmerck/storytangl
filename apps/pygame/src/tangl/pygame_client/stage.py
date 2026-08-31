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

from .models import StageImage, Turn


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
