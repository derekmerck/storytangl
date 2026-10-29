"""Small client-local key descriptions, used directly by their owning handlers."""
from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class KeyBinding:
    """Describe a key combination used by its handler and Help."""

    keys: tuple[int, ...]
    label: str
    description: str
    control: bool = False

    def matches(self, event: pygame.event.Event) -> bool:
        return (event.type == pygame.KEYDOWN and event.key in self.keys
                and (not self.control or bool(event.mod & pygame.KMOD_CTRL)))


HELP = KeyBinding((pygame.K_h,), "Ctrl+H", "Open or close Help", control=True)
PREFERENCE_PAGE = KeyBinding(
    (pygame.K_COMMA,), "Ctrl+,", "Next world-preference page", control=True,
)
PREFERENCE_SHORTCUTS = dict(zip(
    (f"f{number}" for number in range(1, 13)),
    (pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4, pygame.K_F5, pygame.K_F6,
     pygame.K_F7, pygame.K_F8, pygame.K_F9, pygame.K_F10, pygame.K_F11, pygame.K_F12),
    strict=True,
))
