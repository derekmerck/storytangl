"""Run a StoryTangl world in the pygame client.

    PYTHONPATH=engine/src:apps/pygame/src python -m tangl.pygame_client \
        --world repartee_loop --assets worlds/repartee_loop/media

Number keys select a choice, arrows and page keys scroll prose, escape quits.
Every click and choice key resolves to a choice ``edge_id``, never to a bespoke
action, so a hotspot commits the same payload as the numbered list.

A ``pieces`` choice opens a second numbered list; a ``text`` choice opens a focused
editor. Escape leaves either without committing. Only the finished
``(edge_id, payload)`` pair reaches the service,
and it is byte-identical to what the CLI builds for the same choice.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

import pygame

from tangl.presentation.projection import PreferenceDeclaration

from .bridge import (
    PygameSessionBridge,
    UnsupportedAccepts,
    commit_payload,
)
from .models import (
    Action,
    BeginSelection,
    BeginText,
    CancelSelection,
    Commit,
    ConfirmSelection,
    PendingSelection,
    PagePanel,
    PagePreferences,
    PageSelection,
    PreferenceControl,
    PickPiece,
    ScrollText,
    PassagePage,
    TogglePacing,
    SubmitText,
    Turn,
    TogglePreference,
)
from .stage import (
    BACKGROUND_ROLES,
    PORTRAIT_ROLES,
    CANCEL_KEY,
    CONFIRM_KEY,
    PAGE_KEY,
    STAGED_ROLES,
    Stage,
    choice_action,
    position_for_key,
    key_for_position,
)
from .bindings import HELP, PREFERENCE_PAGE, PREFERENCE_SHORTCUTS, KeyBinding
from .chrome import CHROME_KEYS
from .presentation import merge_turns as _merge, visual_passages
from .music import MusicPlayer
from .voice import VoicePlayer
from .text_entry import PendingText, TEXT_KEYS

logger = logging.getLogger(__name__)

MAIN_KEYS = {
    "pacing": KeyBinding((pygame.K_p,), "Ctrl+P", "Switch paged / scrolling reading", True),
    "back": KeyBinding((pygame.K_UP, pygame.K_PAGEUP), "Up / PgUp", "Previous visual page"),
    "forward": KeyBinding((pygame.K_DOWN, pygame.K_PAGEDOWN, pygame.K_SPACE, pygame.K_RETURN),
                          "Down / PgDn / Space / Enter", "Next visual page"),
    "end": KeyBinding((pygame.K_END,), "End", "Skip to the final page / choices"),
    "escape": KeyBinding((pygame.K_ESCAPE,), "Esc", "Exit game, or cancel a pending selection"),
    "panel": KeyBinding((pygame.K_TAB,), "Tab", "Next overflowing state-panel page"),
    "scroll": KeyBinding((pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN),
                         "Up / Down / PgUp / PgDn", "Scroll prose (page keys move a page)"),
}
MUSIC_KEYS = {
    "mute": KeyBinding((pygame.K_m,), "Ctrl+M", "Mute / unmute audio", True),
    "down": KeyBinding((pygame.K_LEFTBRACKET,), "Ctrl+[", "Lower volume by 10%", True),
    "up": KeyBinding((pygame.K_RIGHTBRACKET,), "Ctrl+]", "Raise volume by 10%", True),
}


def _turns(bridge: PygameSessionBridge, envelope) -> list[Turn]:
    return bridge.build_turns(list(getattr(envelope, "fragments", []) or []))


def _frame(bridge: PygameSessionBridge, envelope, previous: Turn | None = None) -> Turn:
    """Merge a batch into one actionable frame and attach its disclosed geometry.

    The ``previous`` frame's room opens the batch as a turn of its own, so a
    response that stages nothing keeps it just as a turn inside a batch would:
    what the player sees does not depend on how the turns were batched. Both
    the map plate and the surface are reference state fetched by name, so they
    are attached here rather than accumulated out of the fragment stream.
    """

    turns = _turns(bridge, envelope)
    if previous is not None:
        room = [image for image in previous.images
                if image.role in BACKGROUND_ROLES + STAGED_ROLES
                or image.role in PORTRAIT_ROLES and image.speaker_id is not None]
        turns = [Turn(step=previous.step, images=room), *turns]
    frame = _merge(turns)
    frame.plate = bridge.map_plate()
    frame.surface = bridge.surface()
    return frame


def _preference_keys(preferences: Sequence[PreferenceDeclaration]) -> dict[int, str]:
    return {
        PREFERENCE_SHORTCUTS[preference.shortcut.casefold()]: preference.preference_id
        for preference in preferences
        if preference.shortcut is not None
        and preference.shortcut.casefold() in PREFERENCE_SHORTCUTS
    }


def _preference_controls(
    bridge: PygameSessionBridge, preferences: Sequence[PreferenceDeclaration],
) -> tuple[PreferenceControl, ...]:
    shortcuts = {identity: pygame.key.name(key).upper()
                 for key, identity in _preference_keys(preferences).items()}
    return tuple(
        PreferenceControl(
            preference_id=preference.preference_id,
            label=preference.label,
            help=preference.help,
            value=bridge.preferences[preference.preference_id],
            shortcut=shortcuts.get(preference.preference_id),
        )
        for preference in preferences
    )


def _help_lines(
    stage: Stage, frame: Turn, pending: PendingSelection | PendingText | None, music: MusicPlayer,
) -> list[str]:
    """Describe the handlers applicable after Help closes, using their actual mappings."""
    text_mode = isinstance(pending, PendingText)
    status_mode = not text_mode and stage.chrome is not None and stage.chrome.open
    ordinary = pending is None and not status_mode
    mode = ("Text entry" if text_mode else "Status details" if status_mode else
            "Piece selection" if pending is not None else "Paged reading" if stage.paged else
            "Scrolling reading")
    active = [f"After closing Help: {mode}", "", "Current client controls"]
    inactive: list[str] = []

    def add(binding: KeyBinding, enabled: bool = True, description: str | None = None) -> None:
        (active if enabled else inactive).append(
            f"{binding.label}: {description or binding.description}"
        )

    add(HELP)
    for binding in MUSIC_KEYS.values():
        add(binding)
    active.append(f"Audio: {'muted' if music.muted else 'unmuted'}, volume {music.volume:.0%}")
    active.append("Window close: exit the application without submitting pending input")
    if text_mode:
        for name, binding in TEXT_KEYS.items():
            add(binding, name == "cancel" or not pending.composition)
        active.append("Typing / TEXTINPUT: insert literal text; IME composition stays uncommitted")
        active.append("Click Cancel: leave the current text field")
        (inactive if pending.composition else active).append("Click Submit: submit text")
    else:
        add(CHROME_KEYS["details"], stage.chrome is not None)
        if status_mode:
            for name in ("close", "entry", "page"):
                enabled = (len(stage.chrome.sections) > 1 if name == "entry" else
                           stage.chrome.detail_pages > 1 if name == "page" else True)
                add(CHROME_KEYS[name], enabled)
            (active if stage.chrome.detail_pages > 1 else inactive).append("Wheel: page status details")
            (active if len(stage.chrome._pages()) > 1 else inactive).append("Click >: next status-row page")
        else:
            add(MAIN_KEYS["escape"], description=("Cancel piece selection without submitting"
                                                if pending is not None else "Exit game"))
            add(MAIN_KEYS["panel"], any(isinstance(action, PagePanel)
                                       for _box, action in stage.hitboxes))
            if isinstance(pending, PendingSelection):
                for index, piece in enumerate(stage.selection_page(frame, pending), 1):
                    active.append(f"{index}: pick {piece.label or piece.text}")
                (active if pending.satisfied else inactive).append(f"{CONFIRM_KEY}: Confirm selection")
                (active if stage.selection_pages(frame, pending) > 1 else inactive).append(
                    f"{PAGE_KEY}: More candidate pieces"
                )
                active.append(f"{CANCEL_KEY}: Cancel piece selection")
                active.append("Click available pieces; reaching the maximum count submits automatically")
                add(MAIN_KEYS["scroll"], stage.max_scroll > 0)
            else:
                add(MAIN_KEYS["pacing"])
                if stage.paged and stage.pages:
                    add(MAIN_KEYS["back"], stage.page_index > 0)
                    add(MAIN_KEYS["forward"], stage.page_index < len(stage.pages) - 1)
                    add(MAIN_KEYS["end"], stage.page_index < len(stage.pages) - 1)
                else:
                    add(MAIN_KEYS["scroll"], stage.max_scroll > 0)
                (active if stage.max_choice_scroll > 0 else inactive).append(
                    f"Shift+{MAIN_KEYS['scroll'].label}: scroll choices"
                )
                active.append("Choice keys follow displayed positions; uppercase uses Shift/Caps")
                for index, choice in enumerate(frame.choices, 1):
                    key = key_for_position(index) or "Click only"
                    (active if stage.choices_ready and choice_action(choice) is not None
                     else inactive).append(f"{key}: {choice.text}")
            (active if stage.max_scroll or stage.max_choice_scroll else inactive).append(
                "Wheel over a text list: scroll that list (not visual pages)"
            )
    add(PREFERENCE_PAGE, ordinary and stage.preference_pages > 1)
    if not text_mode:
        inactive.extend(f"{binding.label}: {binding.description} (text-entry mode)"
                        for binding in TEXT_KEYS.values())
    if not ordinary:
        inactive.append(f"{MAIN_KEYS['pacing'].label}: {MAIN_KEYS['pacing'].description} (gameplay)")
        inactive.append("Displayed choice keys and world F-keys require gameplay focus")
    result = [*active, "", "Not active in this context", *inactive, "", "World preferences (read-only here)"]
    if not stage.preference_controls:
        result.append("No world preferences declared")
    for preference in stage.preference_controls:
        shortcut = (preference.shortcut + (" (inactive in this mode)" if not ordinary else "")
                    if preference.shortcut else "No supported keyboard shortcut")
        result.append(f"{preference.label}: {preference.value_label} — {shortcut}")
        if preference.help:
            result.append(preference.help)
    return result


def _keyed(
    stage: Stage,
    frame: Turn,
    pending: PendingSelection | None,
    number: int,
) -> Action | None:
    """Resolve a number key against whichever numbered list is on screen.

    The renderer numbers every choice, available or not, so the key indexes the
    displayed list rather than a filtered one -- otherwise the number a player
    reads and the number a key selects drift apart.
    """

    if not stage.choices_ready and pending is None:
        return None
    if pending is not None:
        # The control bindings are the ones the renderer draws, so a candidate
        # can never share a number with Confirm or More.
        if number == CANCEL_KEY:
            return CancelSelection()
        if number == CONFIRM_KEY:
            return ConfirmSelection() if pending.satisfied else None
        if number == PAGE_KEY:
            return PageSelection() if stage.selection_pages(frame, pending) > 1 else None
        page = stage.selection_page(frame, pending)
        if number <= len(page):
            return PickPiece(piece_id=page[number - 1].piece_id)
        return None
    if 1 <= number <= len(frame.choices):
        return choice_action(frame.choices[number - 1])
    return None


def _choice_letter(event: pygame.event.Event) -> str:
    """Resolve ASCII gameplay shortcuts even while SDL text input is stopped."""
    if event.unicode or not pygame.K_a <= event.key <= pygame.K_z:
        return event.unicode
    letter = chr(event.key)
    uppercase = bool(event.mod & pygame.KMOD_SHIFT) != bool(event.mod & pygame.KMOD_CAPS)
    return letter.upper() if uppercase else letter


def _apply(
    bridge: PygameSessionBridge,
    stage: Stage,
    frame: Turn,
    pending: PendingSelection | PendingText | None,
    action: Action,
):
    """Advance the input state machine. Returns the new pending state and, when
    the action reached the service, the envelope it produced."""

    if not stage.choices_ready and isinstance(action, (Commit, BeginText, BeginSelection)):
        return pending, None
    match action:
        case PassagePage():
            stage.page(action)
            return pending, None
        case TogglePacing():
            stage.paged = not stage.paged
            if bridge.preferences.get("pacing") in ("paged", "scrolling"):
                bridge.preferences["pacing"] = "paged" if stage.paged else "scrolling"
            return pending, None
        case ScrollText():
            stage.scroll_text(action)
            return pending, None
        case PagePreferences():
            stage.preference_page += 1
            return pending, None
        case TogglePreference(preference_id=preference_id):
            bridge.cycle_preference(preference_id)
            if preference_id == "pacing":
                stage.paged = bridge.preferences["pacing"] == "paged"
            return pending, None
        case CancelSelection():
            return None, None
        case BeginSelection(choice=choice):
            return PendingSelection(choice=choice), None
        case BeginText(choice=choice):
            authored = choice.payload
            text = authored.get("text", "") if isinstance(authored, dict) else ""
            text = text if isinstance(text, str) else ""
            return PendingText(
                choice=choice, text=text, caret=len(text), step=frame.step,
                session=(bridge.user_id, bridge.ledger_id, bridge.world_id),
            ), None
        case SubmitText():
            if not isinstance(pending, PendingText) or not _text_current(pending, bridge, frame):
                return None, None
            if pending.composition:
                pending.error = "Finish composing text before submitting."
                return pending, None
            try:
                payload = commit_payload(pending.choice, [pending.text])
                envelope = bridge.choose(pending.choice.edge_id, payload)
            except ValueError as exc:
                pending.error = str(exc) or "Text was not accepted. Please try again."
                return pending, None
            return None, envelope
        case PageSelection():
            stage.selection_scroll += 1
            return pending, None
        case PagePanel():
            stage.panel_scroll += 1
            return pending, None
        case PickPiece(piece_id=piece_id):
            if pending is None:
                return None, None
            pending.picked.append(piece_id)
            # Only a full selection commits itself. Anything else waits for the
            # player: between ``min`` and ``max`` there is no moment the client
            # can infer, and a ``min=0`` choice must be submittable while empty.
            if not pending.full:
                return pending, None
            return None, _commit_pending(bridge, pending)
        case ConfirmSelection():
            if pending is None or not pending.satisfied:
                return pending, None
            return None, _commit_pending(bridge, pending)
        case Commit(edge_id=edge_id, payload=payload):
            return None, bridge.choose(edge_id, payload)
    return pending, None


def _text_current(editor: PendingText, bridge: PygameSessionBridge, frame: Turn) -> bool:
    return (
        editor.session == (bridge.user_id, bridge.ledger_id, bridge.world_id)
        and editor.step == frame.step
        and any(choice == editor.choice and choice.available for choice in frame.choices)
    )


def _text_input_rect(stage: Stage, editor: PendingText) -> None:
    rect = editor.field_rect
    pygame.key.set_text_input_rect(pygame.Rect(
        stage.window_point(rect.topleft),
        (rect.width * stage.display_scale, rect.height * stage.display_scale),
    ))


def _commit_pending(bridge: PygameSessionBridge, pending: PendingSelection):
    payload = commit_payload(pending.choice, pending.picked)
    return bridge.choose(pending.choice.edge_id, payload)


FRAME_MS = 33
"""Redraw interval while a sprite clip is playing: about thirty frames a second."""


def _next_events(stage: Stage) -> list[pygame.event.Event]:
    """Block for input, or for one animation tick when something is moving.

    The loop used to poll ``event.get()`` with no wait at all, which spun a core
    even on a stage where nothing could change. Now it sleeps on the event queue:
    indefinitely for a still stage, and for one frame interval while a clip plays,
    so animation costs time only while it is actually animating.
    """

    first = pygame.event.wait(FRAME_MS) if stage.animating else pygame.event.wait()
    return [first, *pygame.event.get()]


def _music_key(event: pygame.event.Event, music: MusicPlayer) -> bool:
    """Ctrl shortcuts are local and cannot collide with choice letters or F-keys."""
    if MUSIC_KEYS["mute"].matches(event):
        music.toggle_mute()
    elif MUSIC_KEYS["down"].matches(event) or MUSIC_KEYS["up"].matches(event):
        music.set_volume(music.volume + (-0.1 if MUSIC_KEYS["down"].matches(event) else 0.1))
    else:
        return False
    return True


def _world_title(bridge: PygameSessionBridge) -> str:
    """Use public world branding, never client audio state, as the caption."""
    return (
        (bridge.branding.name if bridge.branding is not None else None)
        or bridge.world_id
        or "StoryTangl"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", default="repartee_loop")
    parser.add_argument("--assets", type=Path, default=None)
    parser.add_argument("--mute", action="store_true", help="start with music muted")
    parser.add_argument("--volume", type=float, default=0.5, help="local music volume, 0 to 1")
    parser.add_argument(
        "--scale",
        type=int,
        default=3,
        help="client-local integer window scale (default: 3)",
    )
    parser.add_argument("--screenshot", type=Path, help="render one frame, save it, and exit")
    parser.add_argument(
        "--reduced-motion",
        action="store_true",
        help="hold each sprite clip on its first frame instead of animating it",
    )
    parser.add_argument(
        "--advance",
        type=int,
        default=0,
        help="take N first-available choices before rendering; for headless checks",
    )
    args = parser.parse_args(argv)
    if args.scale <= 0:
        parser.error("--scale must be a positive integer")
    if not 0 <= args.volume <= 1:
        parser.error("--volume must be between 0 and 1")

    music = MusicPlayer(volume=args.volume, muted=args.mute)
    bridge = PygameSessionBridge(music_player=music, voice_player=VoicePlayer(music))
    try:
        return _play(args, bridge, music)
    finally:
        bridge.close()
        pygame.quit()


def _play(args: argparse.Namespace, bridge: PygameSessionBridge, music: MusicPlayer) -> int:
    logical_size = bridge.stage_extent(args.world)
    preferences = bridge.discover_preferences(args.world)
    preference_keys = _preference_keys(preferences)
    envelope = bridge.start(args.world)
    stage = Stage(
        asset_dir=args.assets,
        logical_size=logical_size,
        display_scale=args.scale,
        title=_world_title(bridge),
        animate=not args.reduced_motion,
        logo_source=bridge.logo_source,
    )
    stage.preference_controls = _preference_controls(bridge, preferences)
    stage.paged = bridge.preferences.get("pacing") == "paged"
    # Gameplay is not text input: the key opening an editor must not also type
    # itself into its buffer. TEXTINPUT starts only once that offer has focus.
    pygame.key.stop_text_input()
    frame = _frame(bridge, envelope)
    passages = visual_passages(bridge, envelope)
    stage.present(frame, passages, media_visibility=bridge.media_visibility())

    for step in range(args.advance):
        # Only choices that commit outright. A typed choice needs a value this
        # flag has no way to supply, and sending its bare activation payload
        # reaches the backend as a malformed move rather than as a skipped turn.
        commits = [
            action
            for choice in frame.choices
            if isinstance(action := choice_action(choice), Commit)
        ]
        if not commits:
            blocked = [
                choice.text
                for choice in frame.choices
                if choice.available
                and (
                    choice_action(choice) is None
                    or isinstance(choice_action(choice), (BeginSelection, BeginText))
                )
            ]
            if blocked:
                print(
                    f"--advance stopped after {step} step(s): "
                    f"{blocked[0]!r} needs a value this flag cannot supply.",
                    file=sys.stderr,
                )
            break
        envelope = bridge.choose(commits[0].edge_id, commits[0].payload)
        previous = frame
        frame = _frame(bridge, envelope, previous)
        passages = visual_passages(bridge, envelope, previous)
        stage.present(frame, passages, media_visibility=bridge.media_visibility())
        pygame.display.set_caption(_world_title(bridge))

    stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                   status_available=bridge.status_available, session_id=bridge.ledger_id,
                   icon_sources=bridge.status_icon_sources, world_id=bridge.world_id)
    stage.draw(frame, media_visibility=bridge.media_visibility())

    if args.screenshot is not None:
        pygame.image.save(stage.window, str(args.screenshot))
        return 0

    pending: PendingSelection | PendingText | None = None
    running = True
    while running:
        stale_text = False
        help_focus_changed = False
        for event in _next_events(stage):
            if event.type == pygame.QUIT:
                running = False
                break
            if bridge.voice_player is not None and bridge.voice_player.handle_event(event):
                continue
            if event.type == pygame.NOEVENT:
                continue
            if stage.help.open:
                if stage.help.handle(event, stage.display_scale):
                    if not stage.help.open:
                        help_focus_changed = True
                        if isinstance(pending, PendingText):
                            pygame.key.start_text_input()
                    stage.draw(frame, pending, media_visibility=bridge.media_visibility())
                    if not stage.help.open and isinstance(pending, PendingText):
                        _text_input_rect(stage, pending)
                continue
            if stage.help.requested(event, stage.display_scale):
                stage.help.show(_help_lines(stage, frame, pending, music))
                help_focus_changed = True
                if isinstance(pending, PendingText):
                    pygame.key.stop_text_input()
                if stage.chrome is not None:
                    stage.chrome.clear_hover()
                stage.draw(frame, pending, media_visibility=bridge.media_visibility())
                continue
            if help_focus_changed and event.type in (pygame.TEXTINPUT, pygame.TEXTEDITING):
                continue
            if isinstance(pending, PendingText) and not _text_current(pending, bridge, frame):
                pending = None
                stale_text = True
                pygame.key.stop_text_input()
                stage.draw(frame, media_visibility=bridge.media_visibility())
            if stale_text:
                continue
            if event.type == pygame.KEYDOWN and _music_key(event, music):
                continue
            if (not isinstance(pending, PendingText) and stage.chrome is not None
                    and stage.chrome.handle_event(event, stage.display_scale)):
                stage.draw(frame, pending, media_visibility=bridge.media_visibility())
                continue
            action: Action | None = None
            if isinstance(pending, PendingText):
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = stage.hit(event.pos)
                else:
                    action = pending.handle(event)
                if action is None:
                    stage.draw(frame, pending, media_visibility=bridge.media_visibility())
                    continue
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = stage.hit(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                action = stage.wheel(pygame.mouse.get_pos(), -event.y)
            elif event.type == pygame.KEYDOWN:
                if pending is None and event.key in preference_keys:
                    bridge.cycle_preference(preference_keys[event.key])
                    if preference_keys[event.key] == "pacing":
                        stage.paged = bridge.preferences["pacing"] == "paged"
                    stage.preference_controls = _preference_controls(bridge, preferences)
                    stage.present(frame, passages, media_visibility=bridge.media_visibility())
                    stage.draw(frame, media_visibility=bridge.media_visibility())
                    continue
                if (pending is None and stage.preference_pages > 1
                        and PREFERENCE_PAGE.matches(event)):
                    action = PagePreferences()
                elif pending is None and MAIN_KEYS["pacing"].matches(event):
                    action = TogglePacing()
                elif (pending is None and stage.paged and stage.pages
                        and any(MAIN_KEYS[name].matches(event) for name in ("back", "forward", "end"))
                        and not event.mod & pygame.KMOD_SHIFT):
                    action = PassagePage(
                        -1 if MAIN_KEYS["back"].matches(event) else 1,
                        end=MAIN_KEYS["end"].matches(event),
                    )
                elif MAIN_KEYS["escape"].matches(event):
                    # Escape leaves a selection before it leaves the game: a
                    # player who opened one by mistake should not have to quit.
                    if pending is not None:
                        pending = None
                        stage.draw(frame, media_visibility=bridge.media_visibility())
                    else:
                        running = False
                elif MAIN_KEYS["panel"].matches(event):
                    action = PagePanel()
                elif MAIN_KEYS["scroll"].matches(event):
                    shifted = bool(event.mod & pygame.KMOD_SHIFT)
                    if not shifted or pending is None:
                        action = ScrollText(
                            "choices" if shifted else "prose",
                            -1 if event.key in (pygame.K_UP, pygame.K_PAGEUP) else 1,
                            page=event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN),
                        )
                elif pygame.K_0 <= event.key <= pygame.K_9:
                    action = _keyed(stage, frame, pending, event.key - pygame.K_0)
                elif (
                    pending is None
                    and not event.mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_GUI)
                    and (position := position_for_key(_choice_letter(event))) is not None
                ):
                    # Letters reach the choice list only. The selection panel
                    # binds digits to its own controls, so a letter there would
                    # mean two things at once.
                    action = _keyed(stage, frame, pending, position)

            if action is None:
                continue
            was_text = isinstance(pending, PendingText)
            pending, envelope = _apply(bridge, stage, frame, pending, action)
            if isinstance(pending, PendingText) and not was_text:
                pygame.key.start_text_input()
                if stage.chrome is not None:
                    stage.chrome.open = False
                    stage.chrome.clear_hover()
            elif was_text and not isinstance(pending, PendingText):
                pygame.key.stop_text_input()
            if isinstance(action, (TogglePreference, TogglePacing)):
                stage.preference_controls = _preference_controls(bridge, preferences)
                stage.present(frame, passages, media_visibility=bridge.media_visibility())
            if envelope is not None:
                previous = frame
                frame = _frame(bridge, envelope, previous)
                passages = visual_passages(bridge, envelope, previous)
                stage.present(frame, passages, media_visibility=bridge.media_visibility())
                stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                               status_available=bridge.status_available, session_id=bridge.ledger_id,
                               icon_sources=bridge.status_icon_sources, world_id=bridge.world_id)
                pygame.display.set_caption(_world_title(bridge))
            stage.draw(frame, pending, media_visibility=bridge.media_visibility())
            if isinstance(pending, PendingText):
                _text_input_rect(stage, pending)
        # Due by the clock, not by a quiet queue: a moving mouse floods the queue
        # with motion events, and a redraw that waited for silence would freeze
        # every clip for as long as the pointer moved.
        if stage.animating and stage.since_drawn_ms() >= FRAME_MS:
            stage.draw(frame, pending, media_visibility=bridge.media_visibility())
    if isinstance(pending, PendingText):
        pygame.key.stop_text_input()
    return 0


if __name__ == "__main__":
    sys.exit(main())
