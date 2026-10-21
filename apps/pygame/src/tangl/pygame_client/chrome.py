"""Client-owned compact chrome over ordinary disclosed projection sections."""

from __future__ import annotations

import pygame

from tangl.presentation.projection import (
    BadgeListValue, BrandingValue, ItemListValue, KvListValue, ProjectedSection,
    ScalarValue, TableValue,
)


def section_text(section: ProjectedSection) -> str:
    """Readable floor without interpreting domain keys or private state."""
    value = section.value
    if isinstance(value, ScalarValue):
        return str(value.value) if value.value is not None else ""
    if isinstance(value, KvListValue):
        return "; ".join(f"{row.key}: {row.value}{' ' + row.unit if row.unit else ''}"
                         for row in value.items)
    if isinstance(value, ItemListValue):
        return "; ".join(f"{item.label}: {item.detail}" if item.detail else item.label
                         for item in value.items)
    if isinstance(value, BadgeListValue):
        return ", ".join(value.items)
    if isinstance(value, TableValue):
        return "; ".join(", ".join(f"{key}: {cell}" for key, cell in zip(value.columns, row))
                         for row in value.rows)
    return str(value.model_dump(mode="json", exclude_none=True))


def wrap_pixels(font: pygame.font.Font, text: str, width: int) -> list[str]:
    """Wrap by font metrics, splitting only tokens that cannot fit a line."""
    rows: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            rows.append("")
        while paragraph:
            low, high = 1, len(paragraph)
            while low < high:
                middle = (low + high + 1) // 2
                if font.size(paragraph[:middle])[0] <= width:
                    low = middle
                else:
                    high = middle - 1
            end = low
            if end < len(paragraph) and (space := paragraph.rfind(" ", 0, end + 1)) > 0:
                end = space
            rows.append(paragraph[:end])
            paragraph = paragraph[end:]
            if paragraph.startswith(" "):
                paragraph = paragraph[1:]
    return rows or [""]


class Chrome:
    """A small shell strip and paged details, not a general channel browser."""

    def __init__(self, width: int, density: int) -> None:
        self.width, self.density = width, density
        self.height = 44 * density
        self.font = pygame.font.Font(None, 11 * density)
        self.sections: list[ProjectedSection] = []
        self.branding = BrandingValue(name="StoryTangl")
        self.logo: pygame.Surface | None = None
        self.selected_id: str | None = None
        self.open = False
        self.page = 0
        self.detail_page = 0
        self.hitboxes: list[tuple[pygame.Rect, str]] = []

    def set_content(
        self, branding: BrandingValue | None, sections: list[ProjectedSection],
        logo: pygame.Surface | None,
    ) -> None:
        self.branding = branding or BrandingValue(name="StoryTangl")
        self.sections, self.logo = sections, logo
        if self.selected_id not in {section.section_id for section in sections}:
            self.selected_id = sections[0].section_id if sections else None
            self.detail_page = 0
        self.page = min(self.page, max(0, (len(sections) - 1) // 6))
        if not sections:
            self.open = False

    def _clip(self, text: str, width: int) -> str:
        if self.font.size(text)[0] <= width:
            return text
        low, high = 0, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if self.font.size(text[:middle] + "...")[0] <= width:
                low = middle
            else:
                high = middle - 1
        return text[:low] + "..."

    def draw(self, shell: pygame.Surface) -> None:
        d = self.density
        shell.fill((26, 28, 44), pygame.Rect(0, 0, self.width, self.height))
        x = 4 * d
        if self.logo is not None:
            size = 10 * d
            factor = min(size / self.logo.get_width(), size / self.logo.get_height())
            logo = pygame.transform.scale(self.logo, (
                max(1, round(self.logo.get_width() * factor)),
                max(1, round(self.logo.get_height() * factor)),
            ))
            shell.blit(logo, (x, d))
            x += 13 * d
        label = self._clip(self.branding.name, self.width - x - 100 * d)
        shell.blit(self.font.render(label, False, (232, 226, 205)), (x, 2 * d))
        help_text = "Ctrl+I: status" if self.sections else ""
        shell.blit(self.font.render(help_text, False, (170, 177, 179)),
                   (self.width - 80 * d, 2 * d))
        self.hitboxes.clear()
        for slot, section in enumerate(self.sections[self.page * 6:self.page * 6 + 6]):
            box = pygame.Rect((slot % 3) * self.width // 3, (12 + 11 * (slot // 3)) * d,
                              self.width // 3, 10 * d)
            selected = section.section_id == self.selected_id
            pygame.draw.rect(shell, (63, 96, 99) if selected else (43, 48, 63), box)
            token = section.hints.icon if section.hints else None
            inset = self._icon(shell, token, box.left + 2 * d, box.top + d)
            text = f"{section.title}: {section_text(section)}"
            shell.blit(self.font.render(self._clip(text, box.width - inset - 6 * d),
                                        False, (232, 226, 205)),
                       (box.left + inset + 3 * d, box.top + d))
            self.hitboxes.append((box, section.section_id))
        if self.sections:
            total = (len(self.sections) + 5) // 6
            text = f"Status {self.page + 1}/{total}  [click here: next]" if total > 1 else ""
            shell.blit(self.font.render(text, False, (170, 177, 179)), (4 * d, 35 * d))
        if self.open:
            self._draw_details(shell)

    def _icon(self, surface: pygame.Surface, token: str | None, x: int, y: int) -> int:
        d = self.density
        colour = (232, 194, 95)
        if token in ("sun", "sunset", "moon"):
            pygame.draw.circle(surface, colour, (x + 4 * d, y + 4 * d), 3 * d)
            if token == "moon":
                pygame.draw.circle(surface, (43, 48, 63), (x + 6 * d, y + 2 * d), 3 * d)
            elif token == "sunset":
                pygame.draw.line(surface, (168, 92, 56), (x, y + 5 * d),
                                 (x + 8 * d, y + 5 * d), 2 * d)
        elif token in ("scene", "calendar", "inventory", "lamp", "key", "bag"):
            pygame.draw.rect(surface, colour, (x + d, y + d, 6 * d, 6 * d), d)
        else:
            return 0  # Unknown suggestions retain the full readable label.
        return 10 * d

    def _draw_details(self, shell: pygame.Surface) -> None:
        section = next(s for s in self.sections if s.section_id == self.selected_id)
        d = self.density
        box = pygame.Rect(6 * d, self.height + 6 * d,
                          self.width - 12 * d, shell.get_height() - self.height - 12 * d)
        lines = wrap_pixels(
            self.font, f"{section.title}\n{section_text(section)}", box.width - 8 * d,
        )
        capacity = max(1, box.height // (10 * d) - 3)
        pages = max(1, (len(lines) + capacity - 1) // capacity)
        self.detail_page %= pages
        box.height = min(box.height, (min(len(lines), capacity) + 3) * 10 * d)
        pygame.draw.rect(shell, (232, 226, 205), box)
        pygame.draw.rect(shell, (63, 96, 99), box, d)
        for index, text in enumerate(lines[self.detail_page * capacity:
                                           (self.detail_page + 1) * capacity]):
            shell.blit(self.font.render(text, False, (26, 28, 44)),
                       (box.left + 4 * d, box.top + (4 + index * 10) * d))
        help_text = f"Tab: next entry | PgUp/PgDn: text {self.detail_page + 1}/{pages} | Esc: close"
        shell.blit(self.font.render(self._clip(help_text, box.width - 8 * d), False, (63, 96, 99)),
                   (box.left + 4 * d, box.bottom - 12 * d))

    def handle_event(self, event: pygame.event.Event, scale: int) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i and event.mod & pygame.KMOD_CTRL:
                self.open = not self.open and bool(self.sections)
                return True
            if self.open:
                if event.key == pygame.K_ESCAPE:
                    self.open = False
                elif event.key == pygame.K_TAB:
                    index = next(i for i, s in enumerate(self.sections)
                                 if s.section_id == self.selected_id)
                    direction = -1 if event.mod & pygame.KMOD_SHIFT else 1
                    index = (index + direction) % len(self.sections)
                    self.selected_id = self.sections[index].section_id
                    self.page, self.detail_page = index // 6, 0
                elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                    self.detail_page += -1 if event.key == pygame.K_PAGEUP else 1
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            point = (event.pos[0] // scale, event.pos[1] // scale)
            for box, section_id in self.hitboxes:
                if box.collidepoint(point):
                    if any(section.section_id == section_id for section in self.sections):
                        self.selected_id = section_id
                        self.open, self.detail_page = True, 0
                    return True
            if point[1] < self.height:
                self.page = (self.page + 1) % max(1, (len(self.sections) + 5) // 6)
                return True
            if self.open:
                self.open = False
                return True
        if self.open and event.type in (pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN):
            if event.type == pygame.MOUSEWHEEL:
                self.detail_page -= event.y
            return True
        return False
