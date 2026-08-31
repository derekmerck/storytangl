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

from .models import StageImage, Turn

LOGICAL_SIZE = (320, 200)
SCALE = 3

BACKGROUND_ROLES = ("narrative_im_landscape", "narrative_im", "cover_im")
PORTRAIT_ROLES = ("dialog_im", "avatar_im")
PORTRAIT_HEIGHT = 112
MARGIN = 10
_DEFAULT_SLOTS = ("left", "right", "mid")

INK = (26, 28, 44)
CREAM = (232, 226, 205)
TEAL = (63, 96, 99)
RUST = (168, 92, 56)
DIM = (120, 118, 110)


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

    def _by_role(
        self, turn: Turn, roles: tuple[str, ...]
    ) -> list[tuple[StageImage, pygame.Surface]]:
        found = []
        for role in roles:
            for image in turn.images:
                if image.role != role:
                    continue
                loaded = self._load(image.source)
                if loaded is None:
                    continue
                if image.flip_h:
                    loaded = pygame.transform.flip(loaded, True, False)
                found.append((image, loaded))
        return found

    # ── drawing ──────────────────────────────────────────────────────────

    def draw(self, turn: Turn) -> None:
        """Render one turn and record choice hitboxes for the input layer."""

        self.hitboxes.clear()
        self._draw_background(turn)
        # Choices are laid out first and always reserved, so a long exchange can
        # never push the only way to continue off the logical surface.
        choices_top = LOGICAL_SIZE[1] - 4 - len(turn.choices) * 11
        self._draw_portraits(turn, floor=choices_top)
        self._draw_lines(turn, floor=choices_top)
        self._draw_choices(turn, top=choices_top)
        pygame.transform.scale(self.surface, self.window.get_size(), self.window)
        pygame.display.flip()

    def _draw_background(self, turn: Turn) -> None:
        backgrounds = self._by_role(turn, BACKGROUND_ROLES)
        if backgrounds:
            surface = backgrounds[0][1]
            self.surface.blit(pygame.transform.scale(surface, LOGICAL_SIZE), (0, 0))
        else:
            self.surface.fill(TEAL)

    def _draw_portraits(self, turn: Turn, *, floor: int) -> None:
        """Place up to two sprites on a shared baseline, preserving aspect."""

        staged = self._by_role(turn, PORTRAIT_ROLES)[:3]
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

    def _draw_lines(self, turn: Turn, *, floor: int) -> None:
        """Draw the most recent lines that fit above ``floor``.

        A merged turn can carry more prose than the surface holds — the dockhand
        contest alone emits five lines. Older lines are dropped rather than
        overflowing, since the CLI floor still carries the full transcript.
        """

        drawn: list[tuple[str, str | None, int]] = []
        total = 0
        for line in reversed(turn.lines):
            heading = None
            if line.speaker is not None:
                heading = f"{line.speaker} ({line.manner})" if line.manner else line.speaker
            height = 4 + (len(self._wrap(line.text, 74)) + (1 if heading else 0)) * 9 + 2
            if total + height > floor - 8:
                break
            drawn.append((line.text, heading, height))
            total += height

        y = floor - total
        for text, heading, _height in reversed(drawn):
            if heading is None:
                y = self._draw_box(text, y, fill=INK, text_colour=CREAM)
            else:
                y = self._draw_box(text, y, fill=CREAM, text_colour=INK, heading=heading)

    def _draw_box(
        self,
        text: str,
        y: int,
        *,
        fill: tuple[int, int, int],
        text_colour: tuple[int, int, int],
        heading: str | None = None,
    ) -> int:
        lines = ([heading] if heading else []) + self._wrap(text, 74)
        height = 4 + len(lines) * 9
        rect = pygame.Rect(6, y, LOGICAL_SIZE[0] - 12, height)
        pygame.draw.rect(self.surface, fill, rect)
        pygame.draw.rect(self.surface, INK, rect, width=1)
        for index, line in enumerate(lines):
            colour = RUST if heading and index == 0 else text_colour
            self.surface.blit(self.font.render(line, False, colour), (rect.x + 3, rect.y + 2 + index * 9))
        return rect.bottom + 2

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
