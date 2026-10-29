"""Client-owned compact chrome over ordinary disclosed projection sections."""

from __future__ import annotations

import pygame

from tangl.presentation.projection import (
    BadgeListValue, BrandingValue, ItemListValue, KvListValue, ProjectedSection,
    ScalarValue, TableValue,
)

BAR = (26, 28, 44)
"""The bar, and every entry on it: the stage's ink, opaque. An entry once drew
on a lighter box of its own, which read as a text wash laid over the bar."""

SELECTED = (63, 96, 99)
"""The one entry that is lit: the one whose details are open."""


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
        self.font = pygame.font.Font(None, 16 * density)
        self.line_height = self.font.get_linesize()
        self.height = max(self.line_height, 10 * density) + 2 * density
        self.sections: list[ProjectedSection] = []
        self.branding = BrandingValue(name="StoryTangl")
        self.logo: pygame.Surface | None = None
        self.icons: dict[str, pygame.Surface] = {}
        self.hovered_id: str | None = None
        self.hover_box: pygame.Rect | None = None
        self._drawn_page: int | None = None
        self.selected_id: str | None = None
        self.open = False
        self.page = 0
        self.detail_page = 0
        self.hitboxes: list[tuple[pygame.Rect, str]] = []
        self.info_box = pygame.Rect(width - 12 * density, 0, 12 * density, self.height)
        self.next_box = pygame.Rect(width - 24 * density, 0, 12 * density, self.height)

    def set_content(
        self, branding: BrandingValue | None, sections: list[ProjectedSection],
        logo: pygame.Surface | None,
        icons: dict[str, pygame.Surface] | None = None,
    ) -> None:
        if sections != self.sections or (icons or {}) != self.icons:
            self.clear_hover()
        self.branding = branding or BrandingValue(name="StoryTangl")
        self.sections, self.logo = sections, logo
        self.icons = icons or {}
        if self.selected_id not in {section.section_id for section in sections}:
            self.selected_id = sections[0].section_id if sections else None
            self.detail_page = 0
        self.page = min(self.page, len(self._pages()) - 1)
        self.hitboxes = [(box, identity) for box, identity in self.hitboxes
                         if identity in {section.section_id for section in sections}]

    def _entry_text(self, section: ProjectedSection) -> str:
        value = section_text(section)
        hints = section.hints
        if hints and hints.icon_only and hints.short_label:
            return hints.short_label
        if hints and hints.placement and not hints.icon_only:
            return value or section.title
        return f"{section.title}: {value}" if value else section.title

    def _entry_width(self, section: ProjectedSection) -> int:
        hints = section.hints
        drawable = hints is not None and (
            hints.icon_media in self.icons or hints.icon in self.ICON_TOKENS
        )
        if hints and hints.icon_only and drawable:
            return 12 * self.density
        icon = 10 * self.density if drawable else 0
        return min(self.width // 3, self.font.size(self._entry_text(section))[0]
                   + icon + 6 * self.density)

    def _pages(self) -> list[list[ProjectedSection]]:
        # Unhinted entries join the start group in provider order. Hints never
        # change identity or the provider order used by keyboard inspection.
        ordered = [section for placement in ("start", "middle", "end")
                   for section in self.sections
                   if (section.hints.placement if section.hints and section.hints.placement
                       else "start") == placement]
        pages: list[list[ProjectedSection]] = [[]]
        used = 0
        capacity = self.width - 28 * self.density
        for section in ordered:
            width = self._entry_width(section)
            if pages[-1] and (used + width > capacity or len(pages[-1]) == 6):
                pages.append([])
                used = 0
            pages[-1].append(section)
            used += width
        return pages

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
        shell.fill(BAR, pygame.Rect(0, 0, self.width, self.height))
        self.hitboxes.clear()
        pages = self._pages()
        self.page %= len(pages)
        if self.page != self._drawn_page:
            self.clear_hover()
            self._drawn_page = self.page
        entries = pages[self.page]
        left, right = 2 * d, self.width - 26 * d
        for placement in ("start", "middle", "end"):
            group = [section for section in entries
                     if (section.hints.placement if section.hints and section.hints.placement
                         else "start") == placement]
            width = sum(self._entry_width(section) for section in group)
            x = left if placement == "start" else max(left, (left + right - width) // 2)
            if placement == "middle":
                end_width = sum(self._entry_width(section) for section in entries
                                if section.hints and section.hints.placement == "end")
                x = min(x, right - end_width - width)
            elif placement == "end":
                x = right - width
            for section in group:
                box = pygame.Rect(x, 0, self._entry_width(section), self.height)
                ground = SELECTED if section.section_id == self.selected_id and self.open \
                    else BAR
                pygame.draw.rect(shell, ground, box)
                hints = section.hints
                token = hints.icon if hints else None
                image = self.icons.get(hints.icon_media) if hints else None
                if image is not None:
                    shell.blit(image, (x + 2*d, (self.height - image.get_height()) // 2))
                    inset = 10 * d
                else:
                    inset = self._icon(
                        shell, token, x + 2 * d, (self.height - 8 * d) // 2, ground,
                    )
                if not (hints and hints.icon_only and inset):
                    text = self._clip(self._entry_text(section), box.width - inset - 4 * d)
                    shell.blit(self.font.render(text, False, (232, 226, 205)),
                               (x + inset + 2 * d, (self.height - self.font.get_height()) // 2))
                self.hitboxes.append((box, section.section_id))
                x = box.right
            left = x
        for box, label in ((self.info_box, "i"), (self.next_box, ">" if len(pages) > 1 else "")):
            shell.blit(self.font.render(label, False, (232, 226, 205)),
                       (box.left + 2 * d, (self.height - self.font.get_height()) // 2))
        if self.open:
            self._draw_details(shell)
        elif self.hovered_id is not None:
            self._draw_hover(shell)

    def clear_hover(self) -> None:
        self.hovered_id, self.hover_box = None, None

    @property
    def hover_text(self) -> str:
        section = next((s for s in self.sections if s.section_id == self.hovered_id), None)
        return self._details_text(section) if section is not None else ""

    @staticmethod
    def _details_text(section: ProjectedSection) -> str:
        return f"{section.title}\n{section_text(section)}"

    def _draw_hover(self, shell: pygame.Surface) -> None:
        anchor = next((box for box, identity in self.hitboxes if identity == self.hovered_id), None)
        if anchor is None:
            self.clear_hover()
            return
        d = self.density
        width = self.width - 12*d
        lines = wrap_pixels(self.font, self.hover_text, width - 8*d)
        capacity = max(1, (shell.get_height() - self.height - 8*d) // self.line_height)
        if len(lines) > capacity:
            lines = [*lines[:capacity - 1], "..."]
        width = min(width, max(self.font.size(line)[0] for line in lines) + 8*d)
        box = pygame.Rect(
            min(anchor.left, self.width - width - 6*d), self.height + 2*d,
            width, len(lines) * self.line_height + 4*d,
        )
        self.hover_box = box
        pygame.draw.rect(shell, (232, 226, 205), box)
        pygame.draw.rect(shell, (63, 96, 99), box, d)
        for index, line in enumerate(lines):
            shell.blit(self.font.render(line, False, BAR),
                       (box.left + 4*d, box.top + 2*d + index * self.line_height))

    ICON_TOKENS = frozenset({"sun", "sunset", "moon", "scene", "calendar", "inventory",
                             "lamp", "key", "bag"})

    def _icon(self, surface: pygame.Surface, token: str | None, x: int, y: int,
              ground: tuple[int, int, int]) -> int:
        """Draw an icon token at `x`, `y` over `ground`; return the width it took."""
        d = self.density
        colour = (232, 194, 95)
        if token in ("sun", "sunset", "moon"):
            pygame.draw.circle(surface, colour, (x + 4 * d, y + 4 * d), 3 * d)
            if token == "moon":
                pygame.draw.circle(surface, ground, (x + 6 * d, y + 2 * d), 3 * d)
            elif token == "sunset":
                pygame.draw.line(surface, (168, 92, 56), (x, y + 5 * d),
                                 (x + 8 * d, y + 5 * d), 2 * d)
        elif token == "lamp":
            pygame.draw.polygon(surface, colour, [(x + 2*d, y), (x + 6*d, y),
                                                 (x + 8*d, y + 5*d), (x, y + 5*d)])
            pygame.draw.line(surface, colour, (x + 4*d, y + 5*d), (x + 4*d, y + 8*d), d)
            pygame.draw.line(surface, colour, (x + d, y + 8*d), (x + 7*d, y + 8*d), d)
        elif token == "key":
            pygame.draw.circle(surface, colour, (x + 2*d, y + 3*d), 2*d, d)
            pygame.draw.line(surface, colour, (x + 4*d, y + 3*d), (x + 8*d, y + 3*d), d)
            pygame.draw.line(surface, colour, (x + 6*d, y + 3*d), (x + 6*d, y + 5*d), d)
            pygame.draw.line(surface, colour, (x + 8*d, y + 3*d), (x + 8*d, y + 5*d), d)
        elif token == "bag":
            pygame.draw.rect(surface, colour, (x + 2*d, y, 4*d, 3*d), d)
            pygame.draw.rect(surface, colour, (x, y + 3*d, 8*d, 5*d), d)
        elif token in ("scene", "calendar", "inventory"):
            pygame.draw.rect(surface, colour, (x + d, y + d, 6 * d, 6 * d), d)
        else:
            return 0  # Unknown suggestions retain the full readable label.
        return 10 * d

    def _draw_details(self, shell: pygame.Surface) -> None:
        section = next((s for s in self.sections if s.section_id == self.selected_id), None)
        d = self.density
        box = pygame.Rect(6 * d, self.height + 6 * d,
                          self.width - 12 * d, shell.get_height() - self.height - 12 * d)
        text = f"{self.branding.name}\n"
        if section is not None:
            text += self._details_text(section)
        text += "\nCtrl+I: details | Tab: next entry | Click >: next row page"
        lines = wrap_pixels(self.font, text, box.width - (24 if self.logo is not None else 8) * d)
        capacity = max(1, box.height // self.line_height - 3)
        pages = max(1, (len(lines) + capacity - 1) // capacity)
        self.detail_page %= pages
        box.height = min(box.height, (min(len(lines), capacity) + 3) * self.line_height)
        pygame.draw.rect(shell, (232, 226, 205), box)
        pygame.draw.rect(shell, (63, 96, 99), box, d)
        for index, text in enumerate(lines[self.detail_page * capacity:
                                           (self.detail_page + 1) * capacity]):
            shell.blit(self.font.render(text, False, (26, 28, 44)),
                       (box.left + 4 * d, box.top + 4 * d + index * self.line_height))
        if self.logo is not None:
            size = 12 * d
            factor = min(size / self.logo.get_width(), size / self.logo.get_height())
            logo = pygame.transform.scale(self.logo, (max(1, round(self.logo.get_width() * factor)),
                                                       max(1, round(self.logo.get_height() * factor))))
            shell.blit(logo, (box.right - size - 2*d, box.top + 2*d))
        help_text = f"Tab: next entry | PgUp/PgDn: text {self.detail_page + 1}/{pages} | Esc: close"
        shell.blit(self.font.render(self._clip(help_text, box.width - 8 * d), False, (63, 96, 99)),
                   (box.left + 4 * d, box.bottom - self.line_height - d))

    def handle_event(self, event: pygame.event.Event, scale: int) -> bool:
        if event.type == pygame.WINDOWLEAVE:
            changed = self.hovered_id is not None
            self.clear_hover()
            return changed
        if event.type == pygame.MOUSEMOTION:
            point = (event.pos[0] // scale, event.pos[1] // scale)
            hovered = next((identity for box, identity in self.hitboxes
                            if box.collidepoint(point)), None) if not self.open else None
            changed = hovered != self.hovered_id
            if changed:
                self.hovered_id, self.hover_box = hovered, None
            return changed
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i and event.mod & pygame.KMOD_CTRL:
                self.clear_hover()
                self.open = not self.open
                return True
            if self.open:
                self.clear_hover()
                if event.key == pygame.K_ESCAPE:
                    self.open = False
                elif event.key == pygame.K_TAB and self.sections:
                    index = next(i for i, s in enumerate(self.sections)
                                 if s.section_id == self.selected_id)
                    direction = -1 if event.mod & pygame.KMOD_SHIFT else 1
                    index = (index + direction) % len(self.sections)
                    self.selected_id = self.sections[index].section_id
                    self.page = next(i for i, page in enumerate(self._pages())
                                     if self.sections[index] in page)
                    self.detail_page = 0
                elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                    self.detail_page += -1 if event.key == pygame.K_PAGEUP else 1
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.clear_hover()
            point = (event.pos[0] // scale, event.pos[1] // scale)
            if self.info_box.collidepoint(point):
                self.open = not self.open
                return True
            if self.next_box.collidepoint(point):
                self.page = (self.page + 1) % len(self._pages())
                self.hitboxes.clear()
                return True
            for box, section_id in self.hitboxes:
                if box.collidepoint(point):
                    if any(section.section_id == section_id for section in self.sections):
                        self.selected_id = section_id
                        self.open, self.detail_page = True, 0
                    return True
            if point[1] < self.height:
                return True
            if self.open:
                self.open = False
                return True
        if self.open and event.type in (pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN):
            if event.type == pygame.MOUSEWHEEL:
                self.detail_page -= event.y
            return True
        return False
