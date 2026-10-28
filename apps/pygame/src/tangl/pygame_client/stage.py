"""Pygame renderer for one :class:`Turn`.

Draws to a 320x200 logical surface and scales up with nearest-neighbour, so the
output sits on a real pixel grid at any window size.

The renderer keys entirely off ``media_role`` and fragment attribution. It holds
no world-specific knowledge: a world with no art still plays, rendering flat
colour plus text.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal
from uuid import UUID

import pygame

from tangl.presentation.projection import BrandingValue, ProjectedSection

from .chrome import Chrome, wrap_pixels
from .text_entry import PendingText, draw_text_entry

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
    BeginText,
    CancelSelection,
    Choice,
    Commit,
    ConfirmSelection,
    MapPlate,
    MapRegion,
    PagePanel,
    PagePreferences,
    PageSelection,
    PendingSelection,
    PreferenceControl,
    Piece,
    PickPiece,
    ScrollText,
    PassagePage,
    TogglePacing,
    StageImage,
    TogglePreference,
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


@dataclass(slots=True, frozen=True)
class _ChoiceRow:
    text: str
    choice: Choice


@dataclass(slots=True)
class _Page:
    """Measured local text rows and their deterministic visual snapshot."""

    turn: Turn
    rows: list[_Row]
    heading: str | None


REFUSED_PIN = "X"
"""What a map region pins when no key commits it. See :meth:`Stage._pin`."""

_DEFAULT_LOGICAL_SIZE = (320, 200)
_SUPPORTED_DENSITIES = {_DEFAULT_LOGICAL_SIZE: 1, (640, 400): 2}

BACKGROUND_ROLES = ("narrative_im", "cover_im")
PORTRAIT_ROLES = ("dialog_im", "avatar_im")
MAP_ROLES = ("map_im",)
"""A plate is full-frame but is not scenery: it is deliberately outside
BACKGROUND_ROLES so a client with no map view never stages it as a backdrop."""

STAGED_ROLES = ("staged_im",)
"""Scenery inhabitants: images placed somewhere in the frame rather than
stationed in a dialog slot.

A separate role because the caps differ and mean different things. A backdrop
is one image by nature; a dialog wants a couple of faces at fixed stations; a
populated room wants as many figures as it has, each somewhere particular. A
staged image is the third case, and putting it in PORTRAIT_ROLES would make it
compete for three stations it never wanted.
"""

STAGED_LIMIT = 12
"""How many staged images one turn may draw.

Not a design limit -- roughly double the busiest hand-authored room -- but a
bound, so a world that generates its cast in a loop degrades by dropping the
tail rather than by drawing for a minute.
"""

_BASE_PORTRAIT_HEADROOM = 24
"""How close to the top of the stage a portrait's head may come.

A portrait draws at the size it was packed and is fitted only when it will not
fit, so this is a ceiling rather than a target. It was arrived at as one: the
old code fitted every portrait to a fixed 112 and then shrank it to clear the
choice list, and 24 is where the top had risen to at the moment that shrinking
began. Keeping the number and dropping the mechanism turns the highest a head
ever went into the highest it may go.
"""
_BASE_GUTTER = 10
"""How far a figure staged by name stands in from the frame's edge.

Staging only. Text keeps its own edge, :data:`_BASE_ROW_TEXT_LEFT`, and every
backing under text comes from :meth:`Stage._backing`; a header washed from the
gutter instead sat inside the rows it heads.
"""
_DEFAULT_SLOTS = ("left", "right", "mid")
_BASE_ROW_HEIGHT = 9
_BASE_PROSE_TOP = 24

_BASE_PANEL_WIDTH = 104
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

def key_for_position(index: int) -> str | None:
    """Return the key bound to a one-based choice position, if there is one.

    One function for the marker a row prints, the pin a map region carries and
    the key the event loop resolves, so a printed key and an accepted key
    cannot come apart. Positions past the alphabet have no key.
    """

    if 1 <= index <= len(CHOICE_KEYS):
        return CHOICE_KEYS[index - 1]
    return None


def position_for_key(key: str) -> int | None:
    """Return the one-based choice position a key selects, if any."""

    # A key that types nothing (a function key, a modifier) arrives as "", and
    # every string contains "": `find` would answer 0, the first choice.
    found = CHOICE_KEYS.find(key) if len(key) == 1 else -1
    return found + 1 if found >= 0 else None


def choice_action(choice: Choice) -> Action | None:
    """Return the action a row for ``choice`` performs, or None if it cannot.

    Three outcomes, and the third is the interesting one. A ``pick`` resolves
    straight to a commit. ``pieces`` and ``text`` choices collect input first. Anything
    this port cannot collect a value for yields None, so the row renders inert
    with its reason rather than committing a guessed payload or crashing the
    frame -- the CLI refuses the same kinds unless handed an explicit payload.
    """

    if not choice.available:
        return None
    if getattr(choice.accepts, "kind", "pick") == "pieces":
        return BeginSelection(choice=choice)
    if getattr(choice.accepts, "kind", "pick") == "text":
        return BeginText(choice=choice)
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

_BASE_SURFACE_CONTOUR = 1
SURFACE_WASH = 140
CHOICE_KEYS = "123456789abcdefghijklmnopqrstuvwyzABCDEFGHIJKLMNOPQRSTUVWYZ"
"""Keys a choice may be bound to, by position.

Digits first because a reader expects them, then lowercase and uppercase letters.
Both `x` and `X` are missing: they mark a row that has no key, and a
key that looks like the absence of one is worse than no key at all.

A printed key is a promise, so a choice past the end of this alphabet prints
no key rather than an ordinal nothing will accept. It stays clickable."""

_BASE_CHOICE_PITCH = 11
"""Vertical step between choice rows, one more than the backing they carry."""

_BASE_ROW_TEXT_LEFT = 8
"""Text inset; backing padding sits outside it, independently of staging."""
_BASE_BACKING_PADDING = 3
_BASE_CONTROL_GAP = 5
_BASE_PAGE_CONTROL_GAP = 8
_BASE_PROSE_WRAP_CLEARANCE = 2
"""Additional right clearance retained for scrolling prose wrapping."""

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


def storytangl_glyph(size: int = 64) -> pygame.Surface:
    """StoryTangl's glyph, the window's icon unless a world brands it.

    Drawn as ``brand/assets/glyph-round.svg`` describes it -- a near-black disc,
    a bold serif G squeezed to 0.82 and turned half round -- rather than
    loaded, since that file sets its G as webfont text and SDL's SVG loader
    draws no text.
    """

    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    centre = (size // 2, size // 2)
    pygame.draw.circle(icon, (0x1A, 0x1A, 0x1A), centre, size // 2)
    pygame.draw.aacircle(icon, (0x1A, 0x1A, 0x1A), centre, size // 2)
    font = pygame.font.SysFont("newsreader,georgia,timesnewroman,serif",
                               round(size * 188 / 240), bold=True)
    letter = font.render("G", True, (0xF6, 0xF3, 0xEA))
    letter = pygame.transform.rotate(pygame.transform.smoothscale(
        letter, (round(letter.get_width() * 0.82), letter.get_height())), 180)
    icon.blit(letter, letter.get_rect(center=centre))
    return icon


_ClipKey = tuple[str, str, str, int]
"""A staged occurrence: role, source, resolved slot, and its count among equals."""


@dataclass(slots=True)
class _ClipPlay:
    """Where one staged occurrence is in its clip."""

    clip: str | None
    started_ms: float
    held_ms: float | None = None
    """Elapsed time frozen by ``pause`` or ``stop``; ``None`` while playing."""

    def elapsed(self, now: float) -> float:
        return self.held_ms if self.held_ms is not None else now - self.started_ms


class Stage:
    """Own the display surface, fonts, and per-frame hit regions."""

    def __init__(
        self,
        asset_dir: Path | None = None,
        *,
        logical_size: tuple[int, int] = _DEFAULT_LOGICAL_SIZE,
        display_scale: int = 3,
        title: str = "StoryTangl",
        clock: Callable[[], float] | None = None,
        animate: bool = True,
        keep_on_screen: bool = True,
        choice_fraction: float = 0.4,
        chrome: bool = False,
        logo_source: str | None = None,
    ) -> None:
        try:
            self.density = _SUPPORTED_DENSITIES[logical_size]
        except KeyError as exc:
            supported = ", ".join(
                f"{width}x{height}" for width, height in sorted(_SUPPORTED_DENSITIES)
            )
            raise ValueError(
                f"pygame does not support logical size {logical_size[0]}x{logical_size[1]}; "
                f"supported sizes: {supported}"
            ) from exc
        if display_scale <= 0:
            raise ValueError("display_scale must be a positive integer")
        if not 0.2 <= choice_fraction <= 0.6:
            raise ValueError("choice_fraction must be between 0.2 and 0.6")
        self.choice_fraction = choice_fraction
        self.logical_size = logical_size
        self.display_scale = display_scale
        self.portrait_headroom = _BASE_PORTRAIT_HEADROOM * self.density
        self.gutter = _BASE_GUTTER * self.density
        self.row_height = _BASE_ROW_HEIGHT * self.density
        self.prose_top = _BASE_PROSE_TOP * self.density
        self.panel_width = _BASE_PANEL_WIDTH * self.density
        self.choice_pitch = _BASE_CHOICE_PITCH * self.density
        self.row_text_left = _BASE_ROW_TEXT_LEFT * self.density
        self.backing_padding = _BASE_BACKING_PADDING * self.density
        self.control_gap = _BASE_CONTROL_GAP * self.density
        self.page_control_gap = _BASE_PAGE_CONTROL_GAP * self.density
        self.prose_wrap_clearance = _BASE_PROSE_WRAP_CLEARANCE * self.density
        self.surface_contour = _BASE_SURFACE_CONTOUR * self.density
        pygame.init()
        self.chrome = Chrome(logical_size[0], self.density) if chrome else None
        self._info_session: UUID | None = None
        self.asset_dir = asset_dir
        self._cache: dict[str, pygame.Surface | None] = {}
        self._icon_source: str | None = logo_source
        logo = self._load(logo_source) if logo_source else None
        # Some platforms accept an icon only before the first window is shown.
        pygame.display.set_icon(logo or storytangl_glyph())
        self.chrome_height = self.chrome.height if self.chrome is not None else 0
        self.window = pygame.display.set_mode(
            (
                self.logical_size[0] * self.display_scale,
                (self.logical_size[1] + self.chrome_height) * self.display_scale,
            )
        )
        pygame.display.set_caption(title)
        self.surface = pygame.Surface(self.logical_size)
        self.shell = pygame.Surface((logical_size[0], logical_size[1] + self.chrome_height))
        self.keep_on_screen = keep_on_screen
        """Hold a *named* position inside the frame when the image is too wide
        to sit there whole. Client policy, not world data: an explicit fraction
        is never adjusted, so an image meant to leave the frame still can."""

        self.font = pygame.font.Font(None, 11 * self.density)
        self.text_font = pygame.font.Font(None, 14 * self.density)
        self.hitboxes: list[tuple[pygame.Rect, Action]] = []
        self.slot_boxes: list[tuple[SurfaceSlot, Piece, pygame.Rect]] = []
        """Where each placed piece was drawn this frame.

        Recorded for the same reason hitboxes are: it is the only honest
        answer to where a piece is, and anything that recomputes it from the
        slot fractions is a second derivation that can drift.
        """
        self.scroll = 0
        self.paged = False
        self.pages: list[_Page] = []
        self.page_index = 0
        self._presentation_frame: Turn | None = None
        self._presentation_visibility: dict[str, bool | str] = {}
        self.max_scroll = 0
        self.prose_capacity = 1
        self.prose_rect = pygame.Rect(0, 0, 0, 0)
        self.choice_scroll = 0
        self.max_choice_scroll = 0
        self.choice_capacity = 1
        self.choice_rect = pygame.Rect(0, 0, 0, 0)
        self.selection_scroll = 0
        self.panel_scroll = 0
        self.prose_floor = self.logical_size[1]
        self.selection_numbers: dict[str, int] = {}
        self.preference_controls: tuple[PreferenceControl, ...] = ()
        self.preference_page = 0
        self._last_turn: Turn | None = None
        self._now: Callable[[], float] = clock or pygame.time.get_ticks
        """Milliseconds. Injected by tests, so no assertion depends on wall time."""
        self.animate = animate
        """False under reduced motion: each clip holds its first frame, still posed."""
        self.animating = False
        """True when the last draw showed a clip that has more frames to play."""
        self._clips: dict[_ClipKey, _ClipPlay] = {}
        self._resident_keys: set[_ClipKey] = set()
        self._staged_turn: Turn | None = None
        """The turn whose portraits were last drawn: a different one is a new statement."""
        self._drawn_at = self._now()
        self._frames: dict[tuple[str, int], pygame.Surface] = {}

    def since_drawn_ms(self) -> float:
        """Milliseconds since the last draw, on the stage's own clock."""

        return self._now() - self._drawn_at

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
                surface = pygame.image.load(str(candidate))
                # Initial window branding is loaded before a display exists.
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha()
            except (pygame.error, OSError):
                surface = None
        self._cache[source] = surface
        return surface

    def _resolve_images(
        self, turn: Turn, media_visibility: Mapping[str, bool | str]
    ) -> tuple[list[tuple[StageImage, pygame.Surface]], list[StageImage]]:
        """Split staged images into drawable surfaces and those that are not.

        An accepted source the renderer cannot load — a remote URL, a missing
        or unreadable file — must not vanish. It degrades to its text floor.
        """

        loaded: list[tuple[StageImage, pygame.Surface]] = []
        unloadable: list[StageImage] = []
        for image in turn.images:
            if image.visibility is not None and media_visibility[image.visibility.preference_id] not in image.visibility.values:
                continue
            clip, client_selected = self._selected_clip(image, media_visibility)
            image = replace(image, clip=clip, client_selected_clip=client_selected)
            surface = self._load(image.source)
            if surface is None:
                unloadable.append(image)
                continue
            if image.flip_h:
                surface = pygame.transform.flip(surface, True, False)
            loaded.append((image, surface))
        return loaded, unloadable

    @staticmethod
    def _selected_clip(
        image: StageImage, preferences: Mapping[str, bool | str]
    ) -> tuple[str | None, bool]:
        binding = image.clip_binding
        if binding is not None:
            values = [preferences[axis] for axis in binding.axes]
            for row in binding.rows:
                if row.values == values:
                    return row.clip, True
            # A missing row deliberately falls back to the authored clip (or
            # still), but it is still a preference-driven selection: changing
            # back and forth must not restart this occurrence's elapsed time.
            return image.clip, True
        return image.clip, False

    @staticmethod
    def _pick(
        loaded: list[tuple[StageImage, pygame.Surface]], roles: tuple[str, ...]
    ) -> list[tuple[StageImage, pygame.Surface]]:
        return [entry for role in roles for entry in loaded if entry[0].role == role]

    # ── drawing ──────────────────────────────────────────────────────────

    @property
    def choices_ready(self) -> bool:
        return not (self.paged and self.pages and self.page_index < len(self.pages) - 1)

    def present(
        self, frame: Turn, passages: list[Turn], *, fresh: bool = True,
        media_visibility: Mapping[str, bool | str] | None = None,
    ) -> None:
        """Prepare fresh local pages once; history/readback never starts a replay."""
        visibility = dict(media_visibility or {})
        same_frame = frame is self._presentation_frame
        if fresh and same_frame and visibility == self._presentation_visibility:
            return
        previous_index = self.page_index if same_frame else 0
        self._presentation_frame = frame
        self._presentation_visibility = visibility
        self.pages = []
        self.page_index = 0
        if not fresh:
            return
        previous_key = None
        width = self.logical_size[0]
        placed = place_pieces(frame.surface, frame.pieces) if frame.surface else []
        if self._has_state(frame, placed=placed):
            width -= self.panel_width
        pixel_width = self.text_bounds(pygame.Rect(0, 0, width, 0)).width
        passages = passages or [frame]
        previous_failed: list[StageImage] = []
        for index, passage in enumerate(passages):
            _, failed = self._resolve_images(passage, visibility)
            # Snapshots carry resident images forward; their caption is not a new arrival.
            arriving_failed = [image for image in failed if image not in previous_failed]
            previous_failed = failed
            fallback = self._rows(Turn(step=passage.step), arriving_failed, pixel_width=pixel_width)
            if not passage.lines and not fallback:
                # A step's last staging is a page of its own only if it shows
                # something the page before does not. A step whose only text the
                # client dropped -- a status echo (#629) -- leaves nothing to see.
                if index + 1 == len(passages) or passages[index + 1].step != passage.step:
                    if self.pages and passage.images != self.pages[-1].turn.images:
                        self.pages.append(_Page(passage, [], None))
                continue
            for line in passage.lines:
                identity = line.speaker_id if line.speaker_id else (
                    id(line) if line.speaker is not None else None
                )
                key = (passage.step, passage.source_id, identity, line.speaker, line.mode,
                       line.manner, line.attitude, line.hints)
                rows = [_Row(part, "dialog" if line.speaker else "narration")
                        for part in self._wrap_pixels(
                            line.text, pixel_width,
                        )]
                heading = line.speaker
                if heading and line.attitude:
                    heading = f"{heading} ({line.attitude})"
                if (self.pages and key == previous_key
                        and passage.images == self.pages[-1].turn.images
                        and len(self.pages[-1].rows) + len(rows) <= 4):
                    self.pages[-1].rows.extend(rows)
                else:
                    for offset in range(0, len(rows), 4):
                        self.pages.append(_Page(passage, rows[offset:offset + 4], heading))
                previous_key = key
            for offset in range(0, len(fallback), 4):
                self.pages.append(_Page(passage, fallback[offset:offset + 4], None))
                previous_key = None
        if not self.pages:
            self.pages = [_Page(frame, [], None)]
        last = self.pages[-1]
        last.turn = replace(frame, lines=last.turn.lines)
        self.page_index = min(previous_index, len(self.pages) - 1)

    def page(self, action: PassagePage) -> None:
        if self.pages:
            self.page_index = len(self.pages) - 1 if action.end else min(
                max(0, self.page_index + action.delta), len(self.pages) - 1,
            )

    def draw(
        self,
        turn: Turn,
        pending: PendingSelection | PendingText | None = None,
        media_visibility: Mapping[str, bool | str] | None = None,
    ) -> None:
        """Render one turn and record its hitboxes for the input layer.

        While ``pending`` is set the choice list is replaced by the pieces that
        choice will accept. That is the second half of the two-step click-pick
        path the Input Parity rule requires: the same numbered list, the same
        keys, and the same payload the CLI would build.
        """

        editor = pending if isinstance(pending, PendingText) else None
        if editor is not None:
            pending = None
        paged = bool(self.paged and self.pages and editor is None and pending is None
                     and turn is self._presentation_frame)
        # Only text to read gets the page's bar. A plate, an encounter, or a
        # response that fits on one page draws as it would scrolling: one page
        # is the whole frame, with the text of every passage it combined.
        if paged and len(self.pages) > 1:
            turn = self.pages[self.page_index].turn
        reading = paged and len(self.pages) > 1 and bool(self.pages[self.page_index].rows)
        self.hitboxes.clear()
        if paged and not reading and not self.choices_ready:
            # Drawn under everything, so any control still wins its own click.
            self.hitboxes.append((self.surface.get_rect(), PassagePage()))
        self.slot_boxes.clear()
        self.animating = False
        self._drawn_at = self._now()
        visibility = media_visibility or {}
        loaded, unloadable = self._resolve_images(turn, visibility)
        # A whole frame captions each image it cannot draw. A page among several
        # captions none: each was captioned on the page it arrived on (`present`).
        captioned = [] if paged and len(self.pages) > 1 else unloadable
        # A map is a way to travel, not a way to pick a document; while a
        # selection is open the plate would offer edges that are not on offer.
        if pending is None and not reading and self._draw_map(turn, loaded, captioned):
            self._draw_preferences()
            # The map replaces the stage, so every sprite has left it: drop their
            # playback, or a clip resumes mid-cycle on the far side of the map.
            self._clips.clear()
            self._staged_turn = None
            if editor is not None:
                self.hitboxes = draw_text_entry(self.surface, editor, self.text_font, self.density)
            elif len(self.pages) > 1 and not self.paged:
                self._draw_pacing_switch()
            self._present()
            return
        self._draw_background(loaded)
        if reading:
            maps = self._pick(loaded, MAP_ROLES)
            plate = (self._plate_surface(turn.plate, maps) if turn.plate else maps[0][1]) if maps else None
            if plate is not None:
                self.surface.blit(pygame.transform.scale(plate, self.logical_size), (0, 0))
                if turn.plate is not None:
                    for index, choice, region in self._claimed_regions(turn, turn.plate):
                        self._draw_region(index, choice, region)
        self._draw_preferences()
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
        choice_rows = self._choice_rows(turn)
        below = (
            self._selection_rows(turn, pending, on_surface=on_surface)
            if pending is not None
            else len(choice_rows)
        )
        bottom = self.logical_size[1] - 4 * self.density
        choice_limit = max(
            2 * self.choice_pitch,
            int((bottom - self.prose_top) * self.choice_fraction),
        )
        choice_height = below * self.choice_pitch
        if pending is None:
            choice_height = min(choice_height, choice_limit)
        choices_top = bottom - choice_height
        # Scenery before faces: an ornament stands in the room, a portrait
        # speaks over it. Both stand on the stage, not on the text: the
        # choice list is drawn over them rather than holding them up.
        fresh = turn is not self._staged_turn
        self._staged_turn = turn
        self._resident_keys = set()
        self._draw_staged(turn, visibility, fresh=fresh)
        self._draw_portraits(turn, visibility, fresh=fresh)
        self._clips = {key: play for key, play in self._clips.items() if key in self._resident_keys}
        panelled = self._has_state(turn, placed=placed)
        width = self.logical_size[0] - (self.panel_width if panelled else 0)
        stage_rect = pygame.Rect(
            0,
            self.prose_top,
            width,
            choices_top - self.prose_top,
        )
        # Recorded because it is a seam: the surface decides it and the prose
        # layout consumes it, and a test that re-derives it from row counts
        # instead passes whether or not the two agree.
        self.prose_floor = self._draw_surface(
            turn, placed, rect=stage_rect, pending=pending, numbers=numbers
        )
        prose_floor = self.prose_floor
        rows = self._rows(
            turn,
            captioned,
            pixel_width=self.text_bounds(stage_rect, clearance=self.prose_wrap_clearance).width,
        )
        capacity = max(1, (prose_floor - self.prose_top) // self.row_height)
        overflow = len(rows) > capacity
        # The header takes a choice's pitch, as it does over choices, so the
        # scene shows between it and the first row.
        body_top = self.prose_top + (self.choice_pitch if overflow else 0)
        if overflow:
            capacity = max(1, (prose_floor - body_top) // self.row_height)
        self.prose_capacity = capacity
        self.prose_rect = pygame.Rect(0, body_top, width, capacity * self.row_height)
        self.max_scroll = max(0, len(rows) - capacity)
        if turn is not self._last_turn:
            self.scroll = 0
            self.choice_scroll = 0
            self._last_turn = turn
        self.scroll = min(max(self.scroll, 0), self.max_scroll)
        if reading:
            self._draw_page(width=width, floor=prose_floor)
        else:
            self._draw_rows(rows[self.scroll : self.scroll + capacity], capacity=capacity, width=width)
        if panelled:
            self._draw_state_panel(
                turn,
                top=2 * self.density,
                bottom=choices_top,
                placed=placed,
            )
        if pending is not None:
            self.choice_rect = pygame.Rect(0, 0, 0, 0)
            self._draw_selection(
                turn, pending, top=choices_top, on_surface=on_surface, numbers=numbers
            )
        else:
            self._draw_choices(choice_rows, top=choices_top, bottom=bottom)
        if editor is not None:
            self.hitboxes = draw_text_entry(self.surface, editor, self.text_font, self.density)
        elif len(self.pages) > 1 and not self.paged:
            self._draw_pacing_switch()
        self._present()

    def _draw_pacing_switch(self) -> None:
        text = self.font.render("Pages (Ctrl+P)", False, CREAM)
        bounds = self.text_bounds(self.surface.get_rect())
        rect = text.get_rect(topright=(bounds.right, 2 * self.density))
        self._wash(rect, INK)
        self._blit_control(text, rect.topleft, bounds, TogglePacing())

    def _draw_page(self, *, width: int, floor: int) -> None:
        page = self.pages[self.page_index]
        # One bar -- the speaker at its left, the page's controls at its right --
        # and the rows directly under it, at the same distance on every page.
        top = max(self.prose_top, floor - 5 * self.row_height)
        panel = pygame.Rect(0, top, width, 5 * self.row_height)
        self.hitboxes.append((panel, PassagePage()))
        self.prose_rect = pygame.Rect(0, top + self.row_height, width, 4 * self.row_height)
        self.prose_capacity, self.max_scroll, self.scroll = 4, 0, 0
        self._draw_rows(page.rows, capacity=len(page.rows), width=width)
        bounds = self.text_bounds(panel)
        controls = [(self.font.render(label, False, CREAM), action) for label, action in (
            (f"{self.page_index + 1}/{len(self.pages)}", None), ("<", PassagePage(-1)),
            (">", PassagePage()), ("End", PassagePage(end=True)), ("Scroll", TogglePacing()),
        )]
        x = bounds.right - sum(text.get_width() for text, _ in controls) \
            - (len(controls) - 1) * self.page_control_gap
        heading = self.font.render(
            self._clip(page.heading or "", width=max(0, x - self.page_control_gap - bounds.left)),
            False, RUST,
        )
        # Backed as the rows beneath it are, so the bar and the text share both
        # edges, as the scrolling header does.
        self._wash(
            self._backing(heading, left=self.row_text_left, y=top, kind="prose",
                          width=width, pitch=self.row_height),
            INK,
        )
        self._blit_control(heading, (bounds.left, top), bounds)
        for text, action in controls:
            self._blit_control(text, (x, top), bounds, action)
            x += text.get_width() + self.page_control_gap

    def set_info(
        self, branding: BrandingValue | None, sections: list[ProjectedSection],
        logo_source: str | None, *, status_available: bool, session_id: UUID | None = None,
    ) -> None:
        """Allocate shell space only for an advertised status channel, even if empty."""
        if logo_source != self._icon_source:
            # Runtime icon changes are best-effort on platforms that support them.
            self._icon_source = logo_source
            logo = self._load(logo_source) if logo_source else None
            pygame.display.set_icon(logo or storytangl_glyph())
        if status_available != (self.chrome is not None) or session_id != self._info_session:
            self.chrome = Chrome(self.logical_size[0], self.density) if status_available else None
            self.chrome_height = self.chrome.height if self.chrome is not None else 0
            self.shell = pygame.Surface((self.logical_size[0],
                                         self.logical_size[1] + self.chrome_height))
            self.window = pygame.display.set_mode((
                self.logical_size[0] * self.display_scale,
                (self.logical_size[1] + self.chrome_height) * self.display_scale,
            ))
            self._info_session = session_id
        if self.chrome is not None:
            self.chrome.set_content(branding, sections, self._load(logo_source) if logo_source else None)

    def _present(self) -> None:
        if self.chrome is not None:
            self.shell.blit(self.surface, (0, self.chrome_height))
            self.chrome.draw(self.shell)
            source = self.shell
        else:
            source = self.surface
        pygame.transform.scale(source, self.window.get_size(), self.window)
        pygame.display.flip()

    def _draw_preferences(self) -> None:
        page_size = 2
        pages = max(1, -(-len(self.preference_controls) // page_size))
        page = self.preference_page % pages
        controls = self.preference_controls[page * page_size : page * page_size + page_size]
        for index, control in enumerate(controls):
            shortcut = f"{control.shortcut}: " if control.shortcut else ""
            help_text = f" — {control.help}" if control.help else ""
            value = "on" if control.value is True else "off" if control.value is False else control.value
            text = f"{shortcut}{control.label}: {value}{help_text}"
            surface = self.font.render(text, False, INK)
            rect = pygame.Rect(
                2 * self.density,
                2 * self.density + index * self.row_height,
                surface.get_width(),
                self.row_height,
            )
            self.surface.blit(surface, rect.topleft)
            self.hitboxes.append((rect, TogglePreference(control.preference_id)))
        if pages > 1:
            label = self.font.render(f"more {page + 1}/{pages}", False, ALERT)
            rect = pygame.Rect(
                self.logical_size[0] - label.get_width() - 2 * self.density,
                2 * self.density,
                label.get_width(),
                self.row_height,
            )
            self.surface.blit(label, rect.topleft)
            self.hitboxes.append((rect, PagePreferences()))

    # ── map view ─────────────────────────────────────────────────────────

    def _draw_map(
        self, turn: Turn, loaded: list[tuple[StageImage, pygame.Surface]],
        captioned: list[StageImage],
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

        self.surface.blit(pygame.transform.scale(surface, self.logical_size), (0, 0))
        claimed = self._claimed_regions(turn, plate)
        for index, choice, region in claimed:
            self._draw_region(index, choice, region)

        self._draw_map_footer(turn, captioned)
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
            round(region.x * self.logical_size[0]),
            round(region.y * self.logical_size[1]),
            max(4 * self.density, round(region.w * self.logical_size[0])),
            max(4 * self.density, round(region.h * self.logical_size[1])),
        )
        # Dim on actionability, not availability: a choice this port cannot
        # collect a value for has no hitbox either, and a live-looking box over
        # dead pixels is exactly the hidden dropped choice the map view refuses
        # elsewhere.
        action = choice_action(choice)
        colour = CREAM if action is not None else DIM
        pygame.draw.rect(self.surface, colour, rect, width=self.density)

        # `x` rather than a number for a refused region, for the same reason
        # its legend row carries one: the pin is the key, and this box has no
        # key. Dimmed box, `x` pin, `x)` row -- the three still tie together.
        text = self.font.render(self._pin(index, choice), False, colour)
        pin = pygame.Rect(
            rect.x + self.density,
            rect.y + self.density,
            text.get_width() + 4 * self.density,
            self.row_height,
        )
        self._wash(pin, INK)
        self.surface.blit(text, (pin.x + 2 * self.density, pin.y))

        if action is not None:
            self.hitboxes.append((rect, action))

    def _draw_map_footer(self, turn: Turn, captioned: list[StageImage]) -> None:
        """Narration and the full numbered legend, bounded and pageable.

        Every choice appears here, including ones that already have a box on
        the plate. That is the Input Parity floor kept literally on screen: the
        same number, the same edge, whichever the reader clicks.

        The footer is capped and scrolls rather than growing without limit —
        an attributed exchange on a map location would otherwise cover the map
        it is drawn over. Paging starts at the bottom so the choices, which are
        the only way to continue, are what a fresh turn shows.
        """

        rows = self._rows(turn, captioned, columns=74)
        rows.extend(
            _Row(self._choice_label(index, choice), "choice")
            for index, choice in enumerate(turn.choices, start=1)
        )
        self.choice_rect = pygame.Rect(0, 0, 0, 0)
        if not rows:
            self.prose_rect = pygame.Rect(0, 0, 0, 0)
            self.max_scroll = self.scroll = 0
            return

        capacity = min(len(rows), MAP_FOOTER_ROWS)
        self.prose_capacity = capacity
        self.prose_rect = pygame.Rect(
            0,
            self.logical_size[1] - capacity * self.row_height - 2 * self.density,
            self.logical_size[0],
            capacity * self.row_height,
        )
        self.max_scroll = max(0, len(rows) - capacity)
        if turn is not self._last_turn:
            self.scroll = self.max_scroll
            self._last_turn = turn
        self.scroll = min(max(self.scroll, 0), self.max_scroll)

        visible = rows[self.scroll : self.scroll + capacity]
        y = self.logical_size[1] - capacity * self.row_height - 2 * self.density
        # Choices are keyed by their number rather than by row order, so a
        # scrolled-away choice stays selectable from the keyboard. Two refused
        # rows with the same text now share a key, since both are labelled
        # `x)`; that is harmless because neither has an action to recover.
        by_label = {
            self._choice_label(index, choice): choice
            for index, choice in enumerate(turn.choices, start=1)
        }
        for row in visible:
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
            self._wash(
                self._backing(
                    text,
                    left=self.row_text_left,
                    y=y,
                    kind=row.kind,
                    width=self.logical_size[0],
                    pitch=self.row_height,
                ),
                INK,
            )
            self.surface.blit(text, (self.row_text_left, y))
            if action is not None:
                rect = pygame.Rect(
                    self.row_text_left,
                    y,
                    text.get_width(),
                    self.row_height,
                )
                self.hitboxes.append((rect, action))
            y += self.row_height

        if self.max_scroll:
            marker = f"{self.scroll + 1}/{self.max_scroll + 1}  \u2191\u2193"
            surface = self.font.render(marker, False, DIM)
            self.surface.blit(
                surface,
                (
                    self.logical_size[0] - surface.get_width() - 4 * self.density,
                    self.logical_size[1]
                    - capacity * self.row_height
                    - self.row_height
                    - 2 * self.density,
                ),
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

        if choice_action(choice) is None:
            return REFUSED_PIN
        return key_for_position(index) or ""

    @staticmethod
    def _marker(index: int, choice: Choice) -> str:
        """Return what goes in front of a row: its key, or that it has none.

        Numbering is positional, so the number a row shows is the key that
        commits it. A row this port cannot commit has no key, and printing its
        position invites a press that silently does nothing — so it prints
        `x)` instead. Live rows therefore run 1, 3, 6 rather than 1, 2, 3: the
        gaps are the refusals, and every number on screen works.

        Settled in the widget vocabulary at §2.6.1 and followed by the CLI, so
        an edge carries the same position in both ports.
        """

        pin = Stage._pin(index, choice)
        if pin == REFUSED_PIN:
            return "x)"
        return f"{pin}." if pin else " "

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
                self.surface,
                CREAM,
                pygame.Rect(band.x, band.y, band.w, self.surface_contour),
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
        pygame.draw.rect(self.surface, edge, box, self.density)

        label = piece.label or piece.piece_id
        if number is not None:
            label = f"{number}. {label}"
        elif not piece.available:
            # The same mark an inactive choice row carries. It says the card is
            # not on offer; the panel row still says why.
            label = f"(x) {label}"
        for index, line in enumerate(
            self._wrap(
                label,
                max(1, (box.w - 4 * self.density) // (4 * self.density)),
            )
        ):
            y = box.y + 3 * self.density + index * self.row_height
            if y + self.row_height > box.bottom:
                break
            self.surface.blit(
                self.font.render(line, False, INK if piece.available else DIM),
                (box.x + 3 * self.density, y),
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
            self.surface.blit(pygame.transform.scale(surface, self.logical_size), (0, 0))
        else:
            self.surface.fill(TEAL)

    def _draw_staged(
        self, turn: Turn, preferences: Mapping[str, bool | str], *, fresh: bool
    ) -> None:
        """Draw placed images at their fractions, nearest last.

        Drawn at natural size: a staged image was conformed to this stage by
        whoever packed it, so rescaling here would be a second opinion about a
        size already decided.

        Depth comes off where a figure's feet land -- lower in the frame is
        nearer, so it draws later -- which is the same painter's rule a surface
        already uses for its slots.

        The key is the resolved baseline, not the hint, so a station and a
        fraction compete on the same terms. Sorting on ``y_frac`` alone gave
        every named level a depth of zero, which let a ``top`` figure paint
        over a ``bottom`` one whenever it happened to arrive later -- the exact
        opposite of the rule, and invisible until two images disagreed about
        which vocabulary to use. So the box is resolved first and ordered
        after.
        """

        staged = [image for image in turn.images if image.role in STAGED_ROLES]
        if not staged:
            return
        # Resolve every authored occurrence first. Visibility controls drawing,
        # not residency: a suppressed alternative keeps its identity and clock.
        # The cap is likewise a visible-pixel budget, not a resident-state cap.
        placed: list[tuple[int, int, int, pygame.Surface]] = []
        occurrences: Counter[tuple[str, str, str]] = Counter()
        for image in staged:
            clip, selected = self._selected_clip(image, preferences)
            image = replace(image, clip=clip, client_selected_clip=selected)
            placement = (
                f"x={image.x_frac:.4f}" if image.x_frac is not None else (image.x_slot or "mid")
            )
            identity = (image.role, image.source, placement)
            key = (*identity, occurrences[identity])
            occurrences[identity] += 1
            visible = image.visibility is None or preferences[image.visibility.preference_id] in image.visibility.values
            admitted = visible and len(placed) < STAGED_LIMIT
            if image.clip is not None or image.clip_binding is not None:
                self._resident_keys.add(key)
            surface = self._load(image.source)
            if surface is None:
                continue
            if image.flip_h:
                surface = pygame.transform.flip(surface, True, False)
            width, height = surface.get_size()
            # An unplaced staged image centres on the floor: it asked to be in
            # the room without saying where, and the middle is the honest
            # reading of that.
            box_x = (
                self._place_x(image, width, "mid")
                if image.x_frac is not None or image.x_slot
                else (self.logical_size[0] - width) // 2
            )
            box_y = (
                self._slot_y(
                    image.y_slot,
                    height,
                    self.logical_size[1],
                    keep=image.keep,
                )
                if image.y_frac is None
                else self._frac_y(image.y_frac, height)
            )
            baseline = box_y + height
            frame, offset = self._clip_frame(
                image, surface.get_size(), key, fresh=fresh, schedule=admitted
            )
            if frame is not None:
                surface = frame
                box_x += offset[0]
                box_y += offset[1]
            if admitted:
                placed.append((baseline, box_x, box_y, surface))
        # Stable, so figures sharing a baseline -- the common case, a room of
        # people on one floor -- keep arrival order rather than shuffling.
        placed.sort(key=lambda entry: entry[0])
        for _, box_x, box_y, surface in placed:
            self.surface.blit(surface, (box_x, box_y))

    def _draw_portraits(
        self,
        turn: Turn,
        preferences: Mapping[str, bool | str],
        *,
        fresh: bool,
    ) -> None:
        """Place up to three sprites on a shared baseline, preserving aspect.

        The still decides where a sprite stands and how big it is. When a clip is
        playing, its frame is drawn over the same box where the manifest's
        placement puts it, so starting, stopping or switching a clip never moves
        the character.

        The baseline is the stage's own bottom, the same one :meth:`_draw_staged`
        uses. A portrait standing on the choice list instead would be a figure
        whose feet move when the turn happens to offer one more option -- and
        holding it clear of the text costs exactly the height the text takes,
        so a long list shrank every face on stage. The list is UI drawn over
        the room; the room does not rest on it.
        """

        staged = [image for image in turn.images if image.role in PORTRAIT_ROLES][:3]
        occurrences: Counter[tuple[str, str, str]] = Counter()
        floor = self.logical_size[1]
        # Natural size, capped. A pack already decided how big a face is for
        # the stage it was conformed to, and the stage is now declared, so
        # re-deciding it here can only resample art that was already right --
        # and at a fraction, which drops rows of pixel art unevenly. The cap is
        # the one thing this client still owes: a portrait taller than the
        # stage has to come down, because nothing else will bring it down.
        ceiling = floor - self.portrait_headroom
        for index, image in enumerate(staged):
            clip, client_selected = self._selected_clip(image, preferences)
            image = replace(image, clip=clip, client_selected_clip=client_selected)
            # A placement wins over a slot. The two are different questions --
            # "which of three stations" versus "where exactly" -- and a world
            # that answered the second should not be re-answered by arrival
            # order. A client that ignores fractions still slots by arrival,
            # which is what honouring a subset of the hints means.
            fallback = _DEFAULT_SLOTS[min(index, len(_DEFAULT_SLOTS) - 1)]
            placement = (
                f"x={image.x_frac:.4f}" if image.x_frac is not None
                else (image.x_slot or fallback)
            )
            placed = (image.role, image.source, placement)
            key = (*placed, occurrences[placed])
            occurrences[placed] += 1
            if image.clip is not None or image.clip_binding is not None:
                self._resident_keys.add(key)

            portrait = self._load(image.source)
            if portrait is None:
                continue
            if image.flip_h:
                portrait = pygame.transform.flip(portrait, True, False)
            height = min(portrait.get_height(), ceiling)
            factor = height / portrait.get_height()
            width = max(1, round(portrait.get_width() * factor))
            box_x = self._place_x(image, width, fallback)
            box_y = (
                self._slot_y(image.y_slot, height, floor, keep=image.keep)
                if image.y_frac is None
                else self._frac_y(image.y_frac, height)
            )

            # One timer per staged occurrence: the same sprite used twice gets two,
            # whether it was placed explicitly or given a default slot by arrival.

            visible = (
                image.visibility is None
                or preferences[image.visibility.preference_id] in image.visibility.values
            )
            drawn, (at_x, at_y) = self._clip_frame(
                image, portrait.get_size(), key, fresh=fresh, schedule=visible
            )
            if drawn is None:
                drawn, at_x, at_y = portrait, 0, 0
            if not visible:
                continue
            scaled = pygame.transform.scale(
                drawn,
                (
                    max(1, round(drawn.get_width() * factor)),
                    max(1, round(drawn.get_height() * factor)),
                ),
            )
            self.surface.blit(scaled, (box_x + round(at_x * factor), box_y + round(at_y * factor)))

    def _clip_frame(
        self,
        image: StageImage,
        still_size: tuple[int, int],
        key: _ClipKey,
        *,
        fresh: bool,
        schedule: bool,
    ) -> tuple[pygame.Surface | None, tuple[int, int]]:
        """The frame this image's clip shows now, and where it goes relative to the still.

        ``None`` means draw the still: no clip asked for, no sheet that has it, or a
        sheet this port cannot use. The still is the floor at every one of those.
        """

        if image.clip is None:
            if image.clip_binding is not None:
                self._play(key, image, fresh=fresh)
            return None, (0, 0)
        sheet = next((s for s in image.sheets if s.manifest.has_clip(image.clip)), None)
        if sheet is None:
            return None, (0, 0)
        manifest = sheet.manifest
        atlas = self._load(sheet.source)
        if atlas is None or atlas.get_size() != (manifest.size.w, manifest.size.h):
            return None, (0, 0)

        play = self._play(key, image, fresh=fresh)
        elapsed = play.elapsed(self._now()) if self.animate else 0
        loop = image.timing == "loop"
        index = manifest.frame_index_at(image.clip, elapsed, loop=loop)

        frame = self._frames.get((sheet.source, index))
        if frame is None:
            r = manifest.frames[index].rect
            frame = atlas.subsurface(pygame.Rect(r.x, r.y, r.w, r.h)).copy()
            self._frames[(sheet.source, index)] = frame
        if image.flip_h:
            # Cut the frame out first, then mirror it. Mirroring the whole sheet
            # would reverse the frame order along with the pixels.
            frame = pygame.transform.flip(frame, True, False)
        at = manifest.placement(index, still_size, flip_h=image.flip_h)

        if schedule and self.animate and play.held_ms is None:
            settles = manifest.settles_at_ms(image.clip, loop=loop)
            if settles is None or elapsed < settles:
                self.animating = True
        return frame, (at.x, at.y)

    def _play(self, key: _ClipKey, image: StageImage, *, fresh: bool) -> "_ClipPlay":
        """This occurrence's playback state, after applying the use's ``media_timing``.

        ``None``, ``start`` and ``loop`` play (from wherever a pause left off);
        ``restart`` plays from the top each time a new turn states it; ``pause``
        holds the frame showing; ``stop`` holds the first frame, and the next play
        starts from there. Whether a clip loops is read separately, at timing.
        """

        now = self._now()
        play = self._clips.get(key)
        if (
            play is None
            or (fresh and image.timing == "restart")
            or (play.clip != image.clip and not image.client_selected_clip)
        ):
            play = _ClipPlay(clip=image.clip, started_ms=now)
            self._clips[key] = play
        else:
            play.clip = image.clip
        if image.timing == "stop":
            play.started_ms, play.held_ms = now, 0.0
        elif image.timing == "pause":
            if play.held_ms is None:
                play.held_ms = now - play.started_ms
        elif play.held_ms is not None:
            play.started_ms, play.held_ms = now - play.held_ms, None
        return play

    def _frac_x(self, frac: float, width: int) -> int:
        """Left edge for an image whose *centre* sits ``frac`` across the stage.

        Centre, not left edge, so the same fraction means the same place
        whatever the image is wide -- and so it agrees with the bottom-centre
        anchor a sprite sheet frame already uses.

        Not clamped. Off-stage is a real position: an image sliding from -0.5
        to 0.2 is an entrance from the left, and every frame of that before it
        arrives is partly outside the frame. Pulling it back would turn the
        entrance into a figure stuck against the edge.
        """

        return round(frac * self.logical_size[0]) - width // 2

    def _frac_y(self, frac: float, height: int) -> int:
        """Top edge for an image whose *bottom* sits ``frac`` down the stage.

        The bottom, because a staged figure stands on something and its
        baseline is the part a placement is about. Unclamped for the same
        reason as :meth:`_frac_x`.
        """

        return round(frac * self.logical_size[1]) - height

    def _place_x(self, image: "StageImage", width: int, fallback: str) -> int:
        """Where this image goes horizontally.

        A fraction is honoured exactly and is never held on screen. Clamping
        preserves what a *name* means -- "right" is still over that way once
        pulled in -- but destroys what a *number* means: an image wider than
        half the stage, pulled into the visible band from 0.75, ends up near
        the middle, which is a different position wearing the same hint.

        A world that does not know the image's size should say a name. That is
        what names are for, and asking for best effort on a coordinate you
        could not honour is the error rather than the clamp's absence.
        """

        if image.x_frac is not None:
            return self._frac_x(image.x_frac, width)
        return self._slot_x(image.x_slot or fallback, width, keep=image.keep)

    def _slot_x(self, slot: str, width: int, keep: str | None = None) -> int:
        """Left edge for a horizontal staging slot. Unknown slots centre.

        A station is advisory and every client reads it its own way. This port
        tucks the outer two against the edge with a gutter and centres the
        rest, which is what it has always done and what worlds staged by name
        already sit at. It is deliberately not a fraction: a name is a request
        about where to stand, not a coordinate, and turning it into one would
        move every figure already placed this way.

        Under :attr:`keep_on_screen` -- or when the image says so -- the result
        is held inside the frame. That liberty applies to names only. A
        fraction is a placement and is honoured exactly, including off-stage.
        """

        hold = self.keep_on_screen if keep is None else keep in ("whole", "width")
        if slot == "left":
            x = self.gutter
        elif slot == "right":
            x = self.logical_size[0] - width - self.gutter
        else:
            x = (self.logical_size[0] - width) // 2
        if hold:
            x = max(0, min(x, self.logical_size[0] - width))
        return x

    def _slot_y(self, slot: str | None, height: int, floor: int,
                keep: str | None = None) -> int:
        """Top edge for a vertical staging level. Unknown levels take the floor.

        The counterpart to :meth:`_slot_x`, and the reason `media_y` was being
        declared and then discarded: a world could say ``bottom`` and this port
        had nowhere to put it.

        ``bottom`` is the shared baseline every staged figure already stands
        on, so the common case is unchanged by naming it.
        """

        hold = self.keep_on_screen if keep is None else keep in ("whole", "height")
        if slot == "top":
            y = self.gutter
        elif slot == "mid":
            y = max(self.gutter, (floor - height) // 2)
        else:
            y = floor - height
        if hold:
            y = max(0, min(y, self.logical_size[1] - height))
        return y

    def _rows(
        self,
        turn: Turn,
        unloadable: list[StageImage],
        *,
        columns: int = 74,
        pixel_width: int | None = None,
    ) -> list[_Row]:
        """Flatten a turn into rendered rows, including media text floors."""

        rows: list[_Row] = []

        def wrap(text: str) -> list[str]:
            if pixel_width is not None:
                return self._wrap_pixels(text, pixel_width)
            return self._wrap(text, columns)

        for line in turn.lines:
            if line.speaker is not None:
                heading = f"{line.speaker} ({line.manner})" if line.manner else line.speaker
                rows.extend(_Row(part, "heading") for part in wrap(heading))
                rows.extend(_Row(part, "dialog") for part in wrap(line.text))
            else:
                rows.extend(_Row(part, "narration") for part in wrap(line.text))
        for image in unloadable:
            text = image.alt_text or f"[{image.role} unavailable]"
            rows.extend(_Row(part, "alt") for part in wrap(text))
        return rows

    def _backing(
        self,
        rendered: pygame.Surface,
        *,
        left: int,
        y: int,
        kind: str,
        width: int,
        pitch: int,
    ) -> pygame.Rect:
        """Return the backing rect for one drawn row.

        A choice hugs its own text, so the scene shows between rows and the
        wash matches the hitbox, which is sized from the same text. Prose is a
        block, because a ragged right edge on wrapped narration reads as
        damage rather than as shape.

        One function for both surfaces. The map legend draws prose and choices
        through the same loop as the scene draws them through two, and before
        this they disagreed: the legend washed every row edge to edge, so a
        plate acquired a slab across its foot while the scene above it showed
        the art between the rows.
        """

        # `left` is where the text starts; the backing begins three pixels
        # before it, for every kind. Prose used to start exactly at its first
        # glyph while a choice was padded, so on one surface the wash hugged
        # the "O" of the narration and cleared the number of the row beneath
        # it. Same padding now, so the two share a left edge.
        if kind == "choice":
            # One pixel short of the pitch, so consecutive rows always show a
            # hairline of scene between them however the caller spaces them.
            # That gap is what makes a row read as a separate thing to click.
            return pygame.Rect(
                max(0, left - self.backing_padding),
                y,
                rendered.get_width() + 2 * self.backing_padding,
                pitch - self.density,
            )
        # Prose spans the region `width` gives, standing in from its right
        # edge as far as from its left, so no caller derives the band itself.
        return pygame.Rect(
            max(0, left - self.backing_padding),
            y,
            width - 2 * (left - self.backing_padding),
            self.row_height,
        )

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

        old_clip = self.surface.get_clip()
        self.surface.set_clip(self.prose_rect)
        y = self.prose_rect.top + max(0, capacity - len(rows)) * self.row_height
        for row in rows:
            fill, colour = _ROW_STYLES[row.kind]
            rendered = self.font.render(row.text, False, colour)
            # The rows' margin, as choices, the legend and the header keep it:
            # a pixel further in, the prose's wash sat inside its own header.
            self._wash(
                self._backing(
                    rendered,
                    left=self.row_text_left,
                    y=y,
                    kind=row.kind,
                    width=width,
                    pitch=self.row_height,
                ),
                fill,
            )
            self.surface.blit(rendered, (self.row_text_left, y))
            y += self.row_height
        self.surface.set_clip(old_clip)
        if self.max_scroll:
            self._text_controls(
                "prose", self.scroll, self.max_scroll, capacity,
                top=self.prose_top, width=width,
            )

    def scroll_by(self, delta: int) -> None:
        """Page through prose. Clamped; a no-op when everything already fits."""

        self.scroll = min(max(self.scroll + delta, 0), self.max_scroll)

    def scroll_text(self, action: ScrollText) -> None:
        if action.region == "choices":
            if not self.choice_rect.height:
                return
            delta = action.delta * (self.choice_capacity if action.page else 1)
            self.choice_scroll = min(max(self.choice_scroll + delta, 0), self.max_choice_scroll)
        else:
            self.scroll_by(action.delta * (self.prose_capacity if action.page else 1))

    def wheel(self, position: tuple[int, int], delta: int) -> ScrollText | None:
        point = self._world_point(position)
        if self.choice_rect.collidepoint(point):
            return ScrollText("choices", delta)
        if self.prose_rect.collidepoint(point):
            return ScrollText("prose", delta)
        return None

    def _text_controls(
        self,
        region: Literal["prose", "choices"],
        offset: int,
        maximum: int,
        capacity: int,
        *,
        top: int,
        width: int,
    ) -> None:
        """Only overflow gets controls; all actions stay local to the client.

        The header is washed as the map legend washes a line, inside the
        frame's margins on both sides. Edge to edge, it was the one slab left
        across the scene above a menu whose rows each hug their text.
        """
        total = maximum + capacity
        label = f"{region} {offset + 1}-{min(offset + capacity, total)}/{total}"
        bounds = self.text_bounds(pygame.Rect(0, top, width, self.row_height))
        controls = [("next >", 1, offset < maximum), ("< prev", -1, offset > 0)]
        reserved = sum(self.font.size(text)[0] + self.control_gap for text, _, _ in controls)
        label = self._clip(label, width=max(0, bounds.width - reserved))
        surface = self.font.render(label, False, CREAM)
        self._wash(
            self._backing(
                surface,
                left=self.row_text_left,
                y=top,
                kind="prose",
                width=width,
                pitch=self.row_height,
            ),
            INK,
        )
        self._blit_control(surface, bounds.topleft, bounds)
        right = bounds.right
        for text, delta, enabled in controls:
            rendered = self.font.render(text, False, CREAM if enabled else DIM)
            left = right - rendered.get_width()
            action = ScrollText(region, delta, page=True) if enabled else None
            self._blit_control(rendered, (left, top), bounds, action)
            right = left - self.control_gap

    def _row(self, marker: str, text: str, *, y: int, colour, action: Action | None) -> None:
        """Draw one numbered row and, when actionable, record its hitbox.

        Rows sit directly on the scene, so they carry their own backing. Prose
        has had one since the beginning; choices did not, and cream text over a
        pale plate -- a sunlit market, a parchment floor -- was unreadable
        exactly where the art was working hardest.
        """

        surface = self.font.render(self._clip(f"{marker} {text}"), False, colour)
        rect = pygame.Rect(
            self.row_text_left,
            y,
            surface.get_width(),
            surface.get_height(),
        )
        self._wash(
            self._backing(
                surface,
                left=self.row_text_left,
                y=y,
                kind="choice",
                width=self.logical_size[0],
                pitch=self.choice_pitch,
            ),
            INK,
        )
        self.surface.blit(surface, rect.topleft)
        if action is not None:
            self.hitboxes.append((rect, action))

    def _choice_rows(self, turn: Turn) -> list[_ChoiceRow]:
        rows: list[_ChoiceRow] = []
        for index, choice in enumerate(turn.choices, start=1):
            marker = self._marker(index, choice) + " "
            label = choice.text
            if reason := (choice.unavailable_reason or unsupported_reason(choice)):
                label = f"{label}  — {reason}"
            width = self.text_bounds(self.surface.get_rect()).width - self.font.size(marker)[0]
            rows.extend(
                _ChoiceRow(marker + part, choice) for part in self._wrap_pixels(label, width)
            )
        return rows

    def _draw_choices(self, rows: list[_ChoiceRow], *, top: int, bottom: int) -> None:
        capacity = max(1, (bottom - top) // self.choice_pitch)
        overflow = len(rows) > capacity
        # The header takes a choice's pitch, not a prose row's, so the scene
        # shows beneath it as it does between choices.
        body_top = top + (self.choice_pitch if overflow else 0)
        if overflow:
            capacity = max(1, (bottom - body_top) // self.choice_pitch)
        self.choice_capacity = capacity
        self.max_choice_scroll = max(0, len(rows) - capacity)
        self.choice_scroll = min(max(self.choice_scroll, 0), self.max_choice_scroll)
        self.choice_rect = pygame.Rect(0, body_top, self.logical_size[0], capacity * self.choice_pitch)
        if not rows:
            self.choice_rect.height = 0
            return
        if overflow:
            self._text_controls(
                "choices", self.choice_scroll, self.max_choice_scroll, capacity,
                top=top, width=self.logical_size[0],
            )
        old_clip = self.surface.get_clip()
        self.surface.set_clip(self.choice_rect)
        for index, row in enumerate(rows[self.choice_scroll:self.choice_scroll + capacity]):
            y = body_top + index * self.choice_pitch
            action = choice_action(row.choice)
            rendered = self.font.render(row.text, False, CREAM if action is not None else DIM)
            self._wash(
                self._backing(
                    rendered, left=self.row_text_left, y=y, kind="choice",
                    width=self.logical_size[0], pitch=self.choice_pitch,
                ),
                INK,
            )
            self.surface.blit(rendered, (self.row_text_left, y))
            rect = pygame.Rect(self.row_text_left, y, rendered.get_width(), self.choice_pitch)
            rect = rect.clip(self.choice_rect).clip(self.surface.get_rect())
            if action is not None and rect.width and rect.height:
                self.hitboxes.append((rect, action))
        self.surface.set_clip(old_clip)

    def _wrap_pixels(self, text: str, width: int) -> list[str]:
        """Wrap by font metrics, splitting oversized tokens without losing characters."""
        return wrap_pixels(self.font, text, width)

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

        left = self.logical_size[0] - self.panel_width
        self._wash(pygame.Rect(left, top, self.panel_width, bottom - top), INK)
        columns = (self.panel_width - 10 * self.density) // (4 * self.density)
        rows = self.panel_rows(turn, columns=columns, placed=placed)
        capacity = max(1, (bottom - top - 4 * self.density) // self.row_height)

        page, pages, visible = self.panel_page(rows, capacity=capacity)

        y = top + 2 * self.density
        for text, colour in visible:
            self.surface.blit(
                self.font.render(text, False, colour),
                (left + 4 * self.density, y),
            )
            y += self.row_height

        if pages > 1:
            label = f"page {page + 1}/{pages}  tab"
            surface = self.font.render(label, False, ALERT)
            rect = pygame.Rect(
                left + 4 * self.density,
                bottom - self.row_height,
                surface.get_width(),
                self.row_height,
            )
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
            y += self.choice_pitch

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
            y += self.choice_pitch

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
            y += self.choice_pitch
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
            y += self.choice_pitch

        self._row(f"{CANCEL_KEY}.", "Cancel", y=y, colour=DIM, action=CancelSelection())

    def hit(self, position: tuple[int, int]) -> Action | None:
        """Map a window click to the action its row performs."""

        logical = self._world_point(position)
        # Reverse draw order: the footer is drawn over the plate, so a legend
        # row sitting on top of a region must win the click it visibly owns.
        for rect, action in reversed(self.hitboxes):
            if rect.collidepoint(logical):
                return action
        return None

    def window_point(self, point: tuple[int, int]) -> tuple[int, int]:
        """Map a logical world point into the shell's window coordinates."""
        return (point[0] * self.display_scale,
                (point[1] + self.chrome_height) * self.display_scale)

    def _world_point(self, point: tuple[int, int]) -> tuple[int, int]:
        return (point[0] // self.display_scale,
                point[1] // self.display_scale - self.chrome_height)

    def text_bounds(self, region: pygame.Rect, *, clearance: int = 0) -> pygame.Rect:
        """Glyph bounds inside a text region; backing padding and staging stay separate."""
        return pygame.Rect(region.left + self.row_text_left, region.top,
                           max(0, region.width - 2 * self.row_text_left - clearance), region.height)

    def _blit_control(
        self, rendered: pygame.Surface, position: tuple[int, int], bounds: pygame.Rect,
        action: Action | None = None,
    ) -> None:
        """Paint and hit-test the same visible glyph rectangle."""
        rect = rendered.get_rect(topleft=position)
        visible = rect.clip(bounds).clip(self.surface.get_clip())
        if visible.width and visible.height:
            self.surface.blit(rendered, visible, visible.move(-rect.x, -rect.y))
            if action is not None:
                self.hitboxes.append((visible, action))

    def _clip(self, text: str, *, width: int | None = None) -> str:
        """Return `text` shortened to its measured text-region width.

        A choice row is one line by construction — the number a reader presses
        has to stay with the words it names — so a long one cannot wrap and
        used to run off the right edge instead, taking the end of the sentence
        with it silently. Trimming to an ellipsis at least says that there was
        more. Measured rather than counted: the font is proportional, so a
        column budget would clip the wrong worlds.
        """

        limit = self.text_bounds(self.surface.get_rect()).width if width is None else width
        if self.font.size(text)[0] <= limit:
            return text
        if self.font.size("…")[0] > limit:
            return ""
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
