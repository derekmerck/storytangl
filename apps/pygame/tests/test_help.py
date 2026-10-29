"""Dedicated Help owns input while preserving the live client interaction beneath it."""
from __future__ import annotations

import argparse
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest

pygame = pytest.importorskip("pygame")

from tangl.persistence import PersistenceManagerFactory
from tangl.presentation.intent import PiecesAccepts, TextAccepts
from tangl.pygame_client import __main__ as client
from tangl.pygame_client.bindings import KeyBinding
from tangl.pygame_client.chrome import CHROME_KEYS
from tangl.pygame_client.models import (
    Choice, Line, PendingSelection, Piece, TogglePreference, Turn,
)
from tangl.pygame_client.music import MusicPlayer
from tangl.pygame_client.stage import CREAM, TEAL, Stage, key_for_position, position_for_key
from tangl.pygame_client.text_entry import PendingText, TEXT_KEYS
from tangl.pygame_client.voice import VoicePlayer
from tangl.service import ServiceManager
from tangl.service.world_registry import pop_manual_world, register_manual_world
from tangl.story import World


def key(code: int, mod: int = 0, unicode: str = "") -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=code, mod=mod, unicode=unicode)


def preferences(paged: bool = False) -> list[dict[str, object]]:
    return [
        {"id": "lighting", "kind": "boolean", "label": "Scene lighting", "default": True,
         "shortcut": "f1", "help": "Use the local lighting presentation."},
        {"id": "pacing", "kind": "enum", "label": "Reading", "values": ["scrolling", "paged"],
         "default": "paged" if paged else "scrolling", "shortcut": "F2"},
        {"id": "mood", "kind": "enum", "label": "Mood", "values": ["day", "night"],
         "default": "day", "shortcut": "F3", "help": "Select an authored visual mood."},
        {"id": "unbound", "kind": "boolean", "label": "Click preference", "default": False},
        {"id": "unsupported", "kind": "boolean", "label": "Unsupported shortcut", "default": True,
         "shortcut": "?", "help": "This shortcut is not supported by pygame."},
        {"id": "last", "kind": "boolean", "label": "Last preference", "default": False,
         "shortcut": "F12", "help": "Long explanation " * 35 + "END OF HELP"},
    ]


def world(size: tuple[int, int], *, paged: bool = False, prefs: bool = True) -> World:
    metadata: dict[str, object] = {"stage_extent": {"width": size[0], "height": size[1]}}
    if prefs:
        metadata["ui_preferences"] = preferences(paged)
    return World.from_script_data(script_data={
        "label": "help_witness", "metadata": metadata,
        "scenes": {"room": {"blocks": {"start": {"content": "The room waits."}}}},
    })


def frame() -> Turn:
    return Turn(step=1, lines=[Line(text="A long readable room. " * 150)], choices=[
        Choice(edge_id=uuid4(), text="Enter an answer", accepts=TextAccepts()),
        Choice(edge_id=uuid4(), text="Select documents", accepts=PiecesAccepts(min=1, max=3)),
        Choice(edge_id=uuid4(), text="Ordinary continuation with a sufficiently long label"),
    ], pieces=[Piece(piece_id=str(index), kind="document", text=f"Document {index}")
               for index in range(12)])


@pytest.fixture(autouse=True)
def display() -> Iterator[None]:
    pygame.init()
    yield
    pygame.quit()


@pytest.mark.parametrize("size,zoom", [((320, 200), 2), ((640, 400), 1)])
@pytest.mark.parametrize("mode", ["scrolling", "paged", "selection", "text", "status"])
@pytest.mark.parametrize("window_close", [False, True])
def test_actual_routing_help_is_modal_and_preserves_every_context(
    size: tuple[int, int], zoom: int, mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    window_close: bool,
) -> None:
    declared = world(size, paged=mode == "paged", prefs=mode != "scrolling")
    register_manual_world(declared)
    manager = ServiceManager(PersistenceManagerFactory.native_in_mem())
    music = MusicPlayer()
    voice = VoicePlayer(music)
    bridge = client.PygameSessionBridge(manager, music_player=music, voice_player=voice)
    query = Mock(wraps=manager.get_world_info)
    monkeypatch.setattr(manager, "get_world_info", query)
    submit = Mock(side_effect=AssertionError("Help submitted a game action"))
    monkeypatch.setattr(bridge, "choose", submit)
    turn = frame()
    monkeypatch.setattr(client, "_frame", lambda *_args: turn)
    monkeypatch.setattr(client, "visual_passages", lambda *_args: [turn])
    monkeypatch.setattr(type(bridge), "status_available", property(lambda _self: mode == "status"))
    draws: list[PendingSelection | PendingText | None] = []
    draw = Stage.draw

    def record(stage: Stage, turn: Turn, pending=None, **kwargs: object) -> None:
        draw(stage, turn, pending, **kwargs)
        draws.append(pending)

    monkeypatch.setattr(Stage, "draw", record)
    complete = Mock(wraps=voice.handle_event)
    monkeypatch.setattr(voice, "handle_event", complete)
    focus: list[str] = []
    start, stop = pygame.key.start_text_input, pygame.key.stop_text_input

    def focus_start() -> None:
        focus.append("start")
        start()

    def focus_stop() -> None:
        focus.append("stop")
        stop()

    monkeypatch.setattr(pygame.key, "start_text_input", focus_start)
    monkeypatch.setattr(pygame.key, "stop_text_input", focus_stop)
    batch = 0
    baseline = None
    pending_before = None
    editor_before = None
    selection_before = None
    layout_before = None
    reads = 0
    local_values = None

    def events(stage: Stage) -> list[pygame.event.Event]:
        nonlocal batch, baseline, pending_before, editor_before, selection_before
        nonlocal layout_before, reads, local_values
        batch += 1
        if batch == 1:
            with manager.open_session(user_id=bridge.user_id) as session:
                baseline = session.ledger.unstructure()
            reads, local_values = query.call_count, dict(bridge.preferences)
            if mode == "text":
                return [key(pygame.K_1), pygame.event.Event(pygame.TEXTINPUT, text="draft ?"),
                        key(pygame.K_LEFT), pygame.event.Event(pygame.TEXTEDITING, text="é", start=1)]
            if mode == "selection":
                return [key(pygame.K_2), key(pygame.K_1)]
            if mode == "paged":
                assert len(stage.pages) > 2
                return [key(pygame.K_DOWN)]
            if mode == "status":
                return [key(pygame.K_i, pygame.KMOD_CTRL)]
            return [key(pygame.K_DOWN)]
        if batch == 2:
            pending_before = draws[-1]
            if mode == "text":
                assert isinstance(pending_before, PendingText)
                editor_before = (pending_before.text, pending_before.caret, pending_before.composition,
                                 pending_before.composition_caret, pending_before.view_start)
            elif mode == "selection":
                assert isinstance(pending_before, PendingSelection)
                selection_before = list(pending_before.picked)
            layout_before = (stage.page_index, stage.scroll, stage.choice_scroll,
                             stage.selection_scroll, stage.panel_scroll, stage.preference_page)
            if mode == "scrolling":
                # Always-visible entry point, independent of branding or status.
                point = tuple(value * zoom for value in stage.help.button_rect.center)
                return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)]
            return [key(pygame.K_h, pygame.KMOD_CTRL),
                    pygame.event.Event(pygame.TEXTINPUT, text="h")]
        if batch == 3:
            assert stage.help.open
            assert draws[-1] is pending_before
            assert any("World preferences" in line for line in stage.help.lines)
            if mode == "scrolling":
                assert "No world preferences declared" in stage.help.lines
            else:
                assert any("Scene lighting: on" in line for line in stage.help.lines)
                assert any("Unsupported shortcut: on — No supported keyboard shortcut" in line
                           for line in stage.help.lines)
            # Find a live underlying hit point that is not a Help navigation button.
            points = [(box.right - 1, box.top + 1) for box, _action in stage.hitboxes]
            point = next((point for point in points if not any(
                control.collidepoint(point[0], point[1] + stage.chrome_height)
                for control, _delta in stage.help.controls
            )), (size[0] // 2, size[1] // 2))
            return [key(pygame.K_3), key(pygame.K_a), key(pygame.K_a, pygame.KMOD_SHIFT, "A"),
                    key(pygame.K_8), key(pygame.K_9), key(pygame.K_0), key(pygame.K_RETURN),
                    key(pygame.K_DELETE), key(pygame.K_p, pygame.KMOD_CTRL),
                    key(pygame.K_COMMA, pygame.KMOD_CTRL), key(pygame.K_F1),
                    key(pygame.K_m, pygame.KMOD_CTRL), key(pygame.K_DOWN, pygame.KMOD_SHIFT),
                    pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=stage.window_point(point)),
                    pygame.event.Event(pygame.MOUSEWHEEL, y=-1),
                    pygame.event.Event(pygame.TEXTINPUT, text="not inserted"),
                    pygame.event.Event(pygame.TEXTEDITING, text="not composed", start=0),
                    pygame.event.Event(voice._end_event)]
        if batch == 4:
            assert stage.help.open
            assert bridge.preferences == local_values and not music.muted
            assert stage.help.scroll > 0
            return [key(pygame.K_PAGEUP), key(pygame.K_PAGEDOWN), key(pygame.K_END)]
        if batch == 5:
            assert stage.help.scroll == len(stage.help.rows) - stage.help.capacity
            if mode != "scrolling":
                assert "END OF HELP" in " ".join(stage.help.rows[-stage.help.capacity:])
            assert stage.help.body_rect.bottom <= stage.shell.get_height()
            pygame.image.save(stage.window, str(tmp_path / f"help-{mode}-{size[0]}-last.png"))
            return [key(pygame.K_HOME)]
        if batch == 6:
            assert stage.help.scroll == 0
            pygame.image.save(stage.window, str(tmp_path / f"help-{mode}-{size[0]}.png"))
            if window_close:
                return [pygame.event.Event(pygame.QUIT)]
            return [key(pygame.K_ESCAPE), pygame.event.Event(pygame.TEXTINPUT, text="h")]
        assert not stage.help.open
        assert draws[-1] is pending_before
        assert (stage.page_index, stage.scroll, stage.choice_scroll, stage.selection_scroll,
                stage.panel_scroll, stage.preference_page) == layout_before
        if mode == "text":
            assert (pending_before.text, pending_before.caret, pending_before.composition,
                    pending_before.composition_caret, pending_before.view_start) == editor_before
            assert focus[-1] == "start"
        if mode == "selection":
            assert pending_before.picked == selection_before
        if mode == "status":
            assert stage.chrome.open  # Esc closed Help, not the underlying details.
        assert query.call_count == reads and not submit.called
        assert any(call.args[0].type == voice._end_event for call in complete.call_args_list)
        with manager.open_session(user_id=bridge.user_id) as session:
            assert session.ledger.unstructure() == baseline
        return [pygame.event.Event(pygame.QUIT)]

    monkeypatch.setattr(client, "_next_events", events)
    args = argparse.Namespace(world=declared.label, assets=None, scale=zoom,
                              reduced_motion=True, advance=0, screenshot=None)
    try:
        assert client._play(args, bridge, music) == 0
        assert not submit.called and query.call_count == reads
        with manager.open_session(user_id=bridge.user_id) as session:
            assert session.ledger.unstructure() == baseline
    finally:
        bridge.close()
        pop_manual_world(declared.label)


def test_shared_binding_data_drives_text_status_and_main_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    from tangl.pygame_client.bindings import HELP
    from tangl.pygame_client.models import BeginText

    stage = Stage(display_scale=1, chrome=True)
    bridge = client.PygameSessionBridge()
    turn = frame()
    editor, _envelope = client._apply(bridge, stage, turn, None, BeginText(turn.choices[0]))
    editor.text, editor.caret = "ab", 2
    replacement = KeyBinding((pygame.K_F4,), "F4", "Move caret left via owner binding")
    monkeypatch.setitem(TEXT_KEYS, "left", replacement)
    editor.handle(key(pygame.K_F4))
    assert editor.caret == 1
    assert "F4: Move caret left via owner binding" in client._help_lines(stage, turn, editor, MusicPlayer())
    monkeypatch.setitem(CHROME_KEYS, "details", KeyBinding(
        (pygame.K_u,), "Ctrl+U", "Status via owner binding", True,
    ))
    assert stage.chrome.handle_event(key(pygame.K_u, pygame.KMOD_CTRL), 1)
    assert stage.chrome.open
    assert "Ctrl+U: Status via owner binding" in client._help_lines(stage, turn, None, MusicPlayer())
    assert HELP.matches(key(pygame.K_h, pygame.KMOD_CTRL))
    assert not HELP.matches(key(pygame.K_h))


def test_help_choice_labels_derive_from_actual_mapping_and_gating() -> None:
    stage = Stage(display_scale=1)
    turn = Turn(step=1, choices=[Choice(edge_id=uuid4(), text=f"Choice {index}") for index in range(1, 66)])
    stage.draw(turn)
    lines = client._help_lines(stage, turn, None, MusicPlayer())
    for index, choice in enumerate(turn.choices, 1):
        marker = key_for_position(index)
        assert f"{marker or 'Click only'}: {choice.text}" in lines
        if marker is not None:
            assert position_for_key(marker) == index
            assert client._keyed(stage, turn, None, position_for_key(marker)).edge_id == choice.edge_id
    assert position_for_key("x") is position_for_key("X") is None
    assert "a: Choice 10" in lines and "A: Choice 35" in lines


def test_preferences_supported_shortcuts_backing_pages_and_refreshed_help(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    declared = world((320, 200))
    register_manual_world(declared)
    bridge = client.PygameSessionBridge(ServiceManager(PersistenceManagerFactory.native_in_mem()))
    turn = Turn(step=1)
    monkeypatch.setattr(client, "_frame", lambda *_args: turn)
    monkeypatch.setattr(client, "visual_passages", lambda *_args: [turn])
    batch = 0

    def events(stage: Stage) -> list[pygame.event.Event]:
        nonlocal batch
        batch += 1
        controls = {control.preference_id: control for control in stage.preference_controls}
        if batch == 1:
            assert controls["lighting"].shortcut == "F1"
            assert controls["unsupported"].shortcut is None
            assert controls["unbound"].shortcut is None
            return [key(pygame.K_COMMA, pygame.KMOD_CTRL)]
        if batch == 2:
            assert stage.preference_page == 1
            assert {action.preference_id for _box, action in stage.hitboxes
                    if isinstance(action, TogglePreference)} == {"mood", "unbound"}
            for box, action in stage.hitboxes:
                if isinstance(action, TogglePreference):
                    pixels = {tuple(stage.surface.get_at((x, y))[:3])
                              for x in range(box.left, box.right)
                              for y in range(box.top, box.bottom)}
                    assert CREAM in pixels  # Light text on the normal dark backing.
                    assert stage.surface.get_at((box.right, box.centery))[:3] != TEAL
            pygame.image.save(stage.window, str(tmp_path / "preference-backing.png"))
            return [key(pygame.K_F1, pygame.KMOD_CTRL), key(pygame.K_F3),
                    key(pygame.K_h, pygame.KMOD_CTRL)]
        if batch == 3:
            assert "Scene lighting: off — F1" in stage.help.lines
            assert "Mood: night — F3" in stage.help.lines
            return [key(pygame.K_F1), key(pygame.K_COMMA, pygame.KMOD_CTRL), key(pygame.K_ESCAPE)]
        if batch == 4:
            return [key(pygame.K_p, pygame.KMOD_CTRL), key(pygame.K_h, pygame.KMOD_CTRL)]
        assert "Reading: paged — F2" in stage.help.lines
        assert not bridge.preferences["lighting"] and bridge.preferences["mood"] == "night"
        assert stage.preference_page == 1
        return [pygame.event.Event(pygame.QUIT)]

    monkeypatch.setattr(client, "_next_events", events)
    args = argparse.Namespace(world=declared.label, assets=None, scale=1,
                              reduced_motion=True, advance=0, screenshot=None)
    try:
        assert client._play(args, bridge, MusicPlayer()) == 0
    finally:
        bridge.close()
        pop_manual_world(declared.label)


def test_no_world_preferences_or_status_still_has_help(tmp_path: Path) -> None:
    stage = Stage(display_scale=1)
    bridge = client.PygameSessionBridge()
    turn = Turn(step=1)
    stage.draw(turn)
    assert stage.chrome is None
    assert stage.surface.get_rect().contains(stage.help.button_rect)
    original = pygame.image.tobytes(stage.surface, "RGB")
    stage.help.show(client._help_lines(stage, turn, None, MusicPlayer()))
    stage.draw(turn)
    assert pygame.image.tobytes(stage.surface, "RGB") == original
    assert "No world preferences declared" in stage.help.lines
    pygame.image.save(stage.window, str(tmp_path / "help-no-world.png"))
