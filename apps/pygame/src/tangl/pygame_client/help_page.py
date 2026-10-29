"""One bounded, read-only client Help page; no story or Service dependency."""
from __future__ import annotations

import pygame

from .bindings import HELP, KeyBinding
from .chrome import wrap_pixels


HELP_KEYS = {
    "up": KeyBinding((pygame.K_UP,), "Up", "Scroll Help up"),
    "down": KeyBinding((pygame.K_DOWN,), "Down", "Scroll Help down"),
    "previous": KeyBinding((pygame.K_PAGEUP,), "PgUp", "Previous Help page"),
    "next": KeyBinding((pygame.K_PAGEDOWN,), "PgDn", "Next Help page"),
    "first": KeyBinding((pygame.K_HOME,), "Home", "First Help row"),
    "last": KeyBinding((pygame.K_END,), "End", "Last Help row"),
    "close": KeyBinding((pygame.K_ESCAPE,), "Esc", "Close Help and resume"),
}


class HelpPage:
    """Keep Help navigation and drawing separate from the story canvas."""

    def __init__(self) -> None:
        self.open = False
        self.lines: list[str] = []
        self.rows: list[str] = []
        self.scroll = 0
        self.capacity = 1
        self.button_rect = pygame.Rect(0, 0, 0, 0)
        self.controls: list[tuple[pygame.Rect, int | None]] = []
        self.body_rect = pygame.Rect(0, 0, 0, 0)

    def show(self, lines: list[str]) -> None:
        self.lines, self.rows = lines, []
        self.scroll = 0
        self.open = True

    def draw_button(
        self, surface: pygame.Surface, font: pygame.font.Font, density: int, offset: int,
    ) -> None:
        text = font.render("Help", False, (232, 226, 205))
        self.button_rect = text.get_rect(topright=(surface.get_width() - 4*density,
                                                  offset + 2*density))
        pygame.draw.rect(surface, (26, 28, 44), self.button_rect.inflate(4*density, 0))
        surface.blit(text, self.button_rect)

    def requested(self, event: pygame.event.Event, scale: int) -> bool:
        return HELP.matches(event) or (
            event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            and self.button_rect.collidepoint(event.pos[0] // scale, event.pos[1] // scale)
        )

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, density: int) -> None:
        d = density
        ink, paper, focus = (26, 28, 44), (232, 226, 205), (63, 96, 99)
        surface.fill(ink)
        panel = surface.get_rect().inflate(-12*d, -12*d)
        pygame.draw.rect(surface, ink, panel)
        pygame.draw.rect(surface, paper, panel, d)
        height = font.get_linesize()
        width = panel.width - 12*d
        instructions = wrap_pixels(font, (
            f"{HELP_KEYS['up'].label}/{HELP_KEYS['down'].label}, "
            f"{HELP_KEYS['previous'].label}/{HELP_KEYS['next'].label}, wheel: read. "
            f"{HELP_KEYS['first'].label}/{HELP_KEYS['last'].label}: first/last. "
            f"{HELP_KEYS['close'].label}/{HELP.label}: close."
        ), width)
        header = ["Help — controls and preferences", *instructions]
        for index, line in enumerate(header):
            surface.blit(font.render(line, False, paper),
                         (panel.left + 6*d, panel.top + 4*d + index * height))
        self.body_rect = pygame.Rect(panel.left + 6*d, panel.top + len(header)*height + 8*d,
                                     width, panel.height - (len(header)+2)*height - 12*d)
        if not self.rows:
            self.rows = [row for line in self.lines for row in wrap_pixels(font, line, width)]
        self.capacity = max(1, self.body_rect.height // height)
        self.scroll = min(max(0, self.scroll), max(0, len(self.rows) - self.capacity))
        previous_clip = surface.get_clip()
        surface.set_clip(self.body_rect)
        for index, row in enumerate(self.rows[self.scroll:self.scroll + self.capacity]):
            surface.blit(font.render(row, False, paper),
                         (self.body_rect.left, self.body_rect.top + index * height))
        surface.set_clip(previous_clip)
        self.controls = []
        left = panel.left + 6*d
        for label, delta in (("< Prev", -1), ("Next >", 1), ("Close", None)):
            text = font.render(label, False, paper)
            box = text.get_rect(topleft=(left, panel.bottom - height - 4*d))
            pygame.draw.rect(surface, focus, box.inflate(4*d, 0))
            surface.blit(text, box)
            self.controls.append((box, delta))
            left = box.right + 12*d
        counter = font.render(f"Row {self.scroll+1}/{len(self.rows)}", False, paper)
        surface.blit(counter, counter.get_rect(bottomright=(panel.right - 6*d, panel.bottom - 4*d)))

    def handle(self, event: pygame.event.Event, scale: int) -> bool:
        previous = self.scroll
        if HELP.matches(event) or HELP_KEYS["close"].matches(event):
            self.open = False
            return True
        if HELP_KEYS["up"].matches(event):
            self.scroll -= 1
        elif HELP_KEYS["down"].matches(event):
            self.scroll += 1
        elif HELP_KEYS["previous"].matches(event):
            self.scroll -= self.capacity
        elif HELP_KEYS["next"].matches(event):
            self.scroll += self.capacity
        elif HELP_KEYS["first"].matches(event):
            self.scroll = 0
        elif HELP_KEYS["last"].matches(event):
            self.scroll = len(self.rows)
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll -= event.y * 3
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            point = (event.pos[0] // scale, event.pos[1] // scale)
            for box, delta in self.controls:
                if box.collidepoint(point):
                    if delta is None:
                        self.open = False
                        return True
                    self.scroll += delta * self.capacity
                    break
        self.scroll = min(max(0, self.scroll), max(0, len(self.rows) - self.capacity))
        return previous != self.scroll
