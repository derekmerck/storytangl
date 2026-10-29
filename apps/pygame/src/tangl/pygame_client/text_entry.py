"""One local single-line editor; no service, world, or persistence policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pygame

from .chrome import wrap_pixels
from .bindings import KeyBinding
from .models import Action, CancelSelection, Choice, SubmitText


TEXT_KEYS = {
    "cancel": KeyBinding((pygame.K_ESCAPE,), "Esc", "Cancel text entry without submitting"),
    "submit": KeyBinding((pygame.K_RETURN, pygame.K_KP_ENTER), "Enter / keypad Enter", "Submit text"),
    "left": KeyBinding((pygame.K_LEFT,), "Left", "Move caret left one code point"),
    "right": KeyBinding((pygame.K_RIGHT,), "Right", "Move caret right one code point"),
    "home": KeyBinding((pygame.K_HOME,), "Home", "Move caret to the beginning"),
    "end": KeyBinding((pygame.K_END,), "End", "Move caret to the end"),
    "backspace": KeyBinding((pygame.K_BACKSPACE,), "Backspace", "Delete before the caret"),
    "delete": KeyBinding((pygame.K_DELETE,), "Delete", "Delete after the caret"),
}


@dataclass(slots=True)
class PendingText:
    """A focused offer's local edit buffer, distinct from a committed argument."""

    choice: Choice
    session: tuple[UUID | None, UUID | None, str | None]
    step: int
    text: str = ""
    caret: int = 0
    composition: str = ""
    composition_caret: int = 0
    error: str = ""
    view_start: int = 0
    field_rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    caret_rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))

    def handle(self, event: pygame.event.Event) -> Action | None:
        """TEXTINPUT alone changes text; TEXTEDITING is uncommitted pre-edit."""
        if event.type == pygame.TEXTINPUT:
            self.text = self.text[:self.caret] + event.text + self.text[self.caret:]
            self.caret += len(event.text)
            self.composition = self.error = ""
        elif event.type == pygame.TEXTEDITING:
            self.composition = event.text
            self.composition_caret = event.start
        elif event.type == pygame.KEYDOWN:
            if TEXT_KEYS["cancel"].matches(event):
                return CancelSelection()
            if self.composition:
                return None
            if TEXT_KEYS["submit"].matches(event):
                return SubmitText()
            if TEXT_KEYS["left"].matches(event):
                self.caret = max(0, self.caret - 1)
            elif TEXT_KEYS["right"].matches(event):
                self.caret = min(len(self.text), self.caret + 1)
            elif TEXT_KEYS["home"].matches(event):
                self.caret = 0
            elif TEXT_KEYS["end"].matches(event):
                self.caret = len(self.text)
            elif TEXT_KEYS["backspace"].matches(event) and self.caret:
                self.text = self.text[:self.caret - 1] + self.text[self.caret:]
                self.caret -= 1
                self.error = ""
            elif TEXT_KEYS["delete"].matches(event):
                self.text = self.text[:self.caret] + self.text[self.caret + 1:]
                self.error = ""
        return None


def _visible_end(font: pygame.font.Font, text: str, start: int, width: int) -> int:
    low, high = start, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if font.size(text[start:middle])[0] <= width:
            low = middle
        else:
            high = middle - 1
    return low


def draw_text_entry(
    surface: pygame.Surface, editor: PendingText, font: pygame.font.Font, density: int,
) -> list[tuple[pygame.Rect, Action]]:
    """Draw a bounded modal and only its own clickable submit/cancel controls."""
    d = density
    ink, paper, focus, error = (26, 28, 44), (240, 232, 210), (63, 96, 99), (198, 76, 56)
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 160))
    surface.blit(shade, (0, 0))
    width, height = surface.get_size()
    panel = pygame.Rect(16 * d, (height - 144 * d) // 2, width - 32 * d, 144 * d)
    pygame.draw.rect(surface, ink, panel)
    pygame.draw.rect(surface, paper, panel, d)
    x, usable = panel.x + 10 * d, panel.width - 20 * d
    for index, line in enumerate(wrap_pixels(font, editor.choice.text, usable)[:2]):
        surface.blit(font.render(line, False, paper), (x, panel.y + 8 * d + index * 14 * d))
    accepts = editor.choice.accepts
    hint = accepts.placeholder or ("Required text" if accepts.required else "Text (optional)")
    hint = wrap_pixels(font, hint, usable)[0]
    surface.blit(font.render(hint, False, paper), (x, panel.y + 38 * d))
    box = pygame.Rect(x, panel.y + 54 * d, usable, 22 * d)
    pygame.draw.rect(surface, paper, box)
    pygame.draw.rect(surface, focus, box, 2 * d)
    editor.field_rect = box.inflate(-8 * d, -6 * d)
    view = editor.field_rect
    # Newlines, if supplied by the text system, are visible marks, never rewritten input.
    visual = (editor.text[:editor.caret] + editor.composition + editor.text[editor.caret:])
    visual = visual.replace("\n", "↵").replace("\r", "↵").replace("\0", "�")
    caret = editor.caret + min(editor.composition_caret, len(editor.composition))
    editor.view_start = min(editor.view_start, caret)
    low, high = editor.view_start, caret
    while low < high:
        middle = (low + high) // 2
        if font.size(visual[middle:caret])[0] <= view.width - 2 * d:
            high = middle
        else:
            low = middle + 1
    editor.view_start = low
    end = _visible_end(font, visual, low, view.width - 2 * d)
    previous_clip = surface.get_clip()
    surface.set_clip(view)
    surface.blit(font.render(visual[low:end], False, ink), view.topleft)
    caret_x = view.x + font.size(visual[low:caret])[0]
    editor.caret_rect = pygame.Rect(caret_x, view.y, d, view.height)
    pygame.draw.rect(surface, focus, editor.caret_rect)
    if editor.composition:
        pygame.draw.line(surface, focus, (view.x, view.bottom - d),
                         (min(view.right, caret_x + d), view.bottom - d), d)
    surface.set_clip(previous_clip)
    for hidden, edge, direction in ((low > 0, box.left + 2 * d, 1),
                                    (end < len(visual), box.right - 2 * d, -1)):
        if hidden:
            pygame.draw.polygon(surface, focus, [(edge, box.centery),
                (edge + direction * d, box.centery - 3 * d),
                (edge + direction * d, box.centery + 3 * d)])
    message = editor.error or ("Composing…" if editor.composition else "Enter: submit   Esc: cancel")
    for index, line in enumerate(wrap_pixels(font, message, usable)[:2]):
        surface.blit(font.render(line, False, error if editor.error else paper),
                     (x, panel.y + 82 * d + index * 14 * d))
    buttons = [
        (pygame.Rect(x, panel.bottom - 30 * d, 100 * d, 20 * d), SubmitText(), "Submit"),
        (pygame.Rect(panel.right - 110 * d, panel.bottom - 30 * d, 100 * d, 20 * d),
         CancelSelection(), "Cancel"),
    ]
    for rect, _action, label in buttons:
        pygame.draw.rect(surface, focus, rect)
        rendered = font.render(label, False, paper)
        surface.blit(rendered, rendered.get_rect(center=rect.center))
    return [(rect, action) for rect, action, _label in buttons]
