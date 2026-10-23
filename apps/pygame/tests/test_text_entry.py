"""Local text editing, focus isolation, and ordinary JSON-backed Action submission."""

from __future__ import annotations

import argparse
import os
from dataclasses import replace
from uuid import uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.presentation.intent import (  # noqa: E402
    EnumValidator, LengthValidator, RegexValidator, TextAccepts,
)
from tangl.pygame_client import __main__ as client  # noqa: E402
from tangl.pygame_client.bridge import PygameSessionBridge, commit_payload  # noqa: E402
from tangl.pygame_client.models import (  # noqa: E402
    BeginText, CancelSelection, Choice, Line, SubmitText, Turn,
)
from tangl.pygame_client.music import MusicPlayer  # noqa: E402
from tangl.pygame_client.stage import Stage, choice_action  # noqa: E402
from tangl.pygame_client.text_entry import PendingText  # noqa: E402
from tangl.service import RuntimeEnvelope  # noqa: E402
from tangl.core import BehaviorRegistry  # noqa: E402
from tangl.journal.fragments import ContentFragment  # noqa: E402
from tangl.persistence import PersistenceManagerFactory  # noqa: E402
from tangl.service import ServiceManager  # noqa: E402
from tangl.service.world_registry import register_manual_world, pop_manual_world  # noqa: E402
from tangl.story import World  # noqa: E402
from tangl.vm.runtime.frame import PhaseCtx  # noqa: E402


def key(code: int, unicode: str = "") -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=code, mod=0, unicode=unicode)


def text(value: str) -> pygame.event.Event:
    return pygame.event.Event(pygame.TEXTINPUT, text=value)


@pytest.fixture(autouse=True)
def display():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture(params=[(320, 200), (640, 400)])
def size(request):
    return request.param


@pytest.fixture(params=[False, True], ids=["no-status", "status"])
def chrome(request):
    return request.param


@pytest.fixture
def harness(monkeypatch, size, chrome):
    """Drive the actual loop; only Service/turn adaptation is replaced here."""
    bridge = PygameSessionBridge()
    bridge.user_id, bridge.ledger_id, bridge.world_id = uuid4(), uuid4(), "text_fixture"
    choice = Choice(edge_id=uuid4(), text="Actually my name is…",
                    accepts=TextAccepts(placeholder="Your name"))
    frame = Turn(step=1, lines=[Line("A room.")], choices=[
        Choice(edge_id=uuid4(), text="Locked", available=False), choice,
        Choice(edge_id=uuid4(), text="An ordinary choice"),
    ])
    calls, draws, focus = [], [], []
    monkeypatch.setattr(bridge, "start", lambda _: RuntimeEnvelope())
    monkeypatch.setattr(bridge, "stage_extent", lambda _: size)
    monkeypatch.setattr(bridge, "discover_preferences", lambda _: [])
    monkeypatch.setattr(type(bridge), "status_available", property(lambda _: chrome))
    monkeypatch.setattr(client, "_frame", lambda *_: frame)

    def choose(edge_id, payload):
        calls.append((edge_id, payload))
        return RuntimeEnvelope()

    monkeypatch.setattr(bridge, "choose", choose)
    monkeypatch.setattr(pygame.key, "start_text_input", lambda: focus.append("start"))
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: focus.append("stop"))
    draw = Stage.draw

    def record(stage, turn, pending=None, **kwargs):
        draw(stage, turn, pending, **kwargs)
        draws.append(pending)

    monkeypatch.setattr(Stage, "draw", record)

    def run(script):
        batches = iter([*script, [pygame.event.Event(pygame.QUIT)]])

        def events(stage):
            batch = next(batches)
            return batch(stage) if callable(batch) else batch

        monkeypatch.setattr(client, "_next_events", events)
        args = argparse.Namespace(world="text_fixture", assets=None, scale=1,
                                  reduced_motion=False, advance=0, screenshot=None)
        client._play(args, bridge, MusicPlayer())

    return bridge, choice, frame, calls, draws, focus, run


@pytest.mark.parametrize("opening", ["keyboard", "mouse"])
def test_keyboard_and_pointer_open_submit_exactly_once(harness, opening):
    bridge, choice, frame, calls, draws, focus, run = harness
    value = "  Dana  Reyes é😀 eof  "

    def open_editor(stage):
        if opening == "keyboard":
            return [key(pygame.K_2)]
        rect = next(rect for rect, action in stage.hitboxes if isinstance(action, BeginText))
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                   pos=stage.window_point(rect.center))]

    def submit(stage):
        if opening == "keyboard":
            return [key(pygame.K_RETURN)]
        rect = next(rect for rect, action in stage.hitboxes if isinstance(action, SubmitText))
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                   pos=stage.window_point(rect.center))]

    run([open_editor, [key(pygame.K_3, "3"), key(pygame.K_b, "b"), text(value)], submit])
    assert calls == [(choice.edge_id, {"text": value})]
    assert focus == ["stop", "start", "stop"]
    assert any(isinstance(pending, PendingText) for pending in draws)
    assert frame.choices[0].available is False  # opening uses original position 2


@pytest.mark.parametrize("cancel", ["keyboard", "mouse"])
def test_cancel_and_background_clicks_do_not_commit(harness, cancel):
    bridge, choice, frame, calls, draws, focus, run = harness

    def click(stage):
        if cancel == "keyboard":
            return [key(pygame.K_ESCAPE)]
        rect = next(rect for rect, action in stage.hitboxes if isinstance(action, CancelSelection))
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                   pos=stage.window_point(rect.center))]

    run([[key(pygame.K_2)], [text("not committed"),
         pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)),
         pygame.event.Event(pygame.MOUSEWHEEL, y=-1), key(pygame.K_F1)], click])
    assert calls == []
    assert focus == ["stop", "start", "stop"]


def test_required_blank_retains_editor_and_retry_is_exact(harness):
    bridge, choice, frame, calls, draws, focus, run = harness

    def inspect_error(stage):
        editor = draws[-1]
        assert isinstance(editor, PendingText)
        assert editor.text == " \t " and "required" in editor.error.lower()
        return [key(pygame.K_HOME), key(pygame.K_DELETE), key(pygame.K_DELETE),
                key(pygame.K_DELETE), text("eof"), key(pygame.K_RETURN)]

    run([[key(pygame.K_2)], [text(" \t "), key(pygame.K_RETURN)], inspect_error])
    assert calls == [(choice.edge_id, {"text": "eof"})]
    assert focus == ["stop", "start", "stop"]


def test_optional_empty_is_a_real_submission(harness):
    bridge, choice, frame, calls, draws, focus, run = harness
    frame.choices[1] = replace(choice, accepts=TextAccepts(required=False))
    run([[key(pygame.K_2), key(pygame.K_RETURN)]])
    assert calls == [(choice.edge_id, {"text": ""})]


def test_letter_shortcuts_work_before_and_after_text_focus_without_unicode(harness):
    bridge, choice, frame, calls, draws, focus, run = harness
    ordinary = Choice(edge_id=uuid4(), text="Ordinary B")
    frame.choices[:] = [Choice(edge_id=uuid4(), text=f"Choice {index}")
                        for index in range(9)] + [choice, ordinary]
    run([[key(pygame.K_a), text("buffer, not a move"), key(pygame.K_ESCAPE)],
         [key(pygame.K_b)]])
    assert calls == [(ordinary.edge_id, {})]
    assert focus == ["stop", "start", "stop"]


@pytest.mark.parametrize(("mod", "expected"), [
    (0, "a"), (pygame.KMOD_SHIFT, "A"), (pygame.KMOD_CAPS, "A"),
    (pygame.KMOD_SHIFT | pygame.KMOD_CAPS, "a"),
])
def test_gameplay_letter_mapping_without_text_input(mod, expected):
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="", mod=mod)
    assert client._choice_letter(event) == expected


def test_backend_rejection_keeps_same_buffer_and_caret_for_retry(harness, monkeypatch):
    bridge, choice, frame, calls, draws, focus, run = harness
    attempts = []

    def choose(edge_id, payload):
        attempts.append((edge_id, payload))
        if len(attempts) == 1:
            raise ValueError("That name is already in use.")
        calls.append((edge_id, payload))
        return RuntimeEnvelope()

    monkeypatch.setattr(bridge, "choose", choose)

    def retry(stage):
        editor = draws[-1]
        assert editor.text == " Dana " and editor.caret == len(editor.text)
        assert editor.error == "That name is already in use."
        return [key(pygame.K_BACKSPACE), text(" Reyes "), key(pygame.K_RETURN)]

    run([[key(pygame.K_2), text(" Dana "), key(pygame.K_RETURN)], retry])
    assert attempts == [(choice.edge_id, {"text": " Dana "}),
                        (choice.edge_id, {"text": " Dana Reyes "})]
    assert calls == [attempts[-1]]
    assert focus == ["stop", "start", "stop"]


def test_composition_is_preedit_not_submitted_text(harness):
    bridge, choice, frame, calls, draws, focus, run = harness

    def composing(stage):
        editor = draws[-1]
        assert editor.text == "" and editor.composition == "名"
        return [pygame.event.Event(pygame.TEXTEDITING, text="", start=0, length=0),
                text("名前"), key(pygame.K_RETURN)]

    run([[key(pygame.K_2), pygame.event.Event(pygame.TEXTEDITING, text="名", start=1, length=0),
          key(pygame.K_RETURN)], composing])
    assert calls == [(choice.edge_id, {"text": "名前"})]


@pytest.mark.parametrize("replacement", [
    "user", "ledger", "world", "withdraw", "unavailable", "replace", "step",
])
def test_stale_edits_cannot_submit_or_trigger_underlying_choices(harness, replacement):
    bridge, choice, frame, calls, draws, focus, run = harness

    def replace_offer(stage):
        if replacement == "user":
            bridge.user_id = uuid4()
        elif replacement == "ledger":
            bridge.ledger_id = uuid4()
        elif replacement == "world":
            bridge.world_id = "another_world"
        elif replacement == "withdraw":
            frame.choices.remove(choice)
        elif replacement == "unavailable":
            frame.choices[1] = replace(choice, available=False)
        elif replacement == "replace":
            frame.choices[1] = replace(choice, payload={"new_offer": True})
        else:
            frame.step += 1
        return [key(pygame.K_RETURN), text("stale"), key(pygame.K_3)]

    run([[key(pygame.K_2), text("old buffer")], replace_offer])
    assert calls == []
    assert focus == ["stop", "start", "stop"]


def test_same_offer_restatement_and_local_redraw_keep_buffer(harness):
    bridge, choice, frame, calls, draws, focus, run = harness

    def redraw(stage):
        editor = draws[-1]
        frame.choices[1] = replace(choice)
        bridge.preferences["local_redraw"] = True
        stage.draw(frame, editor, media_visibility=bridge.media_visibility())
        assert draws[-1] is editor and editor.text == "unchanged"
        return [key(pygame.K_RETURN)]

    run([[key(pygame.K_2), text("unchanged")], redraw])
    assert calls == [(choice.edge_id, {"text": "unchanged"})]
    assert focus == ["stop", "start", "stop"]


def test_window_close_discards_pending_without_commit(harness):
    bridge, choice, frame, calls, draws, focus, run = harness
    run([[key(pygame.K_2), text("not submitted")]])
    assert calls == [] and focus == ["stop", "start", "stop"]


def test_prefill_and_editor_keys_preserve_full_value_and_horizontal_view(size, chrome, tmp_path):
    choice = Choice(edge_id=uuid4(), text="Actually my name is…", accepts=TextAccepts(),
                    payload={"text": "old", "operation": "rename"})
    bridge = PygameSessionBridge()
    turn = Turn(step=1, choices=[choice])
    stage = Stage(logical_size=size, chrome=chrome, display_scale=1)
    editor, envelope = client._apply(bridge, stage, turn, None, BeginText(choice))
    assert editor.text == "old" and editor.caret == 3 and envelope is None
    editor.handle(key(pygame.K_HOME))
    editor.handle(key(pygame.K_DELETE))
    editor.handle(text("D"))
    editor.handle(key(pygame.K_RIGHT))
    editor.handle(key(pygame.K_BACKSPACE))
    assert editor.text == "Dd" and editor.caret == 1
    editor.handle(key(pygame.K_END))
    value = " Dana Reyes é😀 " * 50
    editor.handle(text(value))
    editor.error = "A bounded, readable backend validation message."
    stage.draw(turn, editor)
    assert editor.text == "Dd" + value
    assert editor.view_start > 0
    assert editor.field_rect.contains(editor.caret_rect)
    assert stage.surface.get_rect().contains(editor.field_rect)
    assert all(stage.surface.get_rect().contains(rect) for rect, _ in stage.hitboxes)
    assert {type(action) for _, action in stage.hitboxes} == {SubmitText, CancelSelection}
    pygame.image.save(stage.window, str(tmp_path / f"text-{size[0]}-chrome-{chrome}.png"))
    editor.handle(key(pygame.K_HOME))
    stage.draw(turn, editor)
    assert editor.view_start == 0 and editor.text == "Dd" + value


def test_text_payload_never_duplicates_activation_merge():
    choice = Choice(edge_id=uuid4(), text="Name", accepts=TextAccepts(),
                    payload={"text": "default", "operation": "rename", "kept": 7})
    assert commit_payload(choice, ["  Dana  Reyes "]) == {"text": "  Dana  Reyes "}
    assert choice_action(choice) == BeginText(choice)


def test_unrelated_submission_exception_is_not_swallowed(harness, monkeypatch):
    bridge, choice, frame, calls, draws, focus, run = harness

    def broken(*_):
        raise RuntimeError("unrelated failure")

    monkeypatch.setattr(bridge, "choose", broken)
    with pytest.raises(RuntimeError, match="unrelated failure"):
        run([[key(pygame.K_2), text("Dana"), key(pygame.K_RETURN)]])


NAME = "  Dana  Reyes é😀 eof  "


@pytest.mark.parametrize(("accepts", "bad", "good", "message"), [
    (TextAccepts(), " \t ", NAME, "required"),
    (TextAccepts(validators=[LengthValidator(max=32)]), "x" * 33, NAME, "at most"),
    (TextAccepts(validators=[RegexValidator(pattern="Dana")]), "other", NAME, "pattern"),
    (TextAccepts(required=False, validators=[LengthValidator(min=2)]), "", NAME, "at least"),
    (TextAccepts(validators=[LengthValidator(max=1)]), "😀😀", "😀", "at most"),
    (TextAccepts(validators=[EnumValidator(values=[NAME], case_sensitive=True)]),
     "Dana", NAME, "one of"),
    (TextAccepts(required=False), None, "", ""),
])
def test_real_json_name_action_rejects_then_retries_without_duplicate_effects(
    monkeypatch, accepts, bad, good, message,
):
    world = World.from_script_data(script_data={
        "label": "pygame_name_json", "metadata": {"start_at": "intro.start"},
        "globals": {"player_name": "Before", "activation": {}, "effect_count": 0},
        "scenes": {"intro": {"blocks": {
            "start": {"content": "Who are you?", "actions": [{
                "text": "Actually my name is…", "successor": "end",
                "accepts": accepts.model_dump(mode="python"),
                "payload": {"operation": "rename", "kept": 7},
                "effects": ["graph.locals['player_name'] = submitted['text']",
                            "graph.locals['activation'] = submitted.copy()",
                            "graph.locals['effect_count'] += 1"],
            }]},
            "end": {"content": "Named."},
        }}},
    })
    authority = BehaviorRegistry(label="pygame_name_namespace")

    def submitted(*, ctx: PhaseCtx, **_):
        return {"submitted": ctx.selected_payload}

    authority.register(submitted, task="gather_ns")
    world.extra_authorities.append(authority)
    register_manual_world(world)
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="json_sqlite_in_mem",
    )
    manager = ServiceManager(persistence)
    bridge = PygameSessionBridge(manager)
    draws, sent, queries = [], [], []
    draw = Stage.draw
    resolve = manager.resolve_choice
    world_info, story_info = manager.get_world_info, manager.get_story_info

    def record_draw(stage, turn, pending=None, **kwargs):
        draw(stage, turn, pending, **kwargs)
        draws.append(pending)

    def record_resolve(**kwargs):
        sent.append(kwargs["request"].payload)
        return resolve(**kwargs)

    def read_world(*args, **kwargs):
        queries.append("world")
        return world_info(*args, **kwargs)

    def read_story(*args, **kwargs):
        queries.append("story")
        return story_info(*args, **kwargs)

    monkeypatch.setattr(Stage, "draw", record_draw)
    monkeypatch.setattr(manager, "resolve_choice", record_resolve)
    monkeypatch.setattr(manager, "get_world_info", read_world)
    monkeypatch.setattr(manager, "get_story_info", read_story)
    phase = 0
    baseline = None
    lookup_count = 0

    def events(stage):
        nonlocal phase, baseline, lookup_count
        phase += 1
        if phase == 1:
            baseline = persistence.storage[bridge.ledger_id]
            lookup_count = len(queries)
            return [key(pygame.K_1), text(bad if bad is not None else good)]
        if phase == 2:
            assert len(queries) == lookup_count  # no keystroke/redraw lookups
            return [key(pygame.K_RETURN)]
        if phase == 3 and bad is not None:
            editor = draws[-1]
            assert isinstance(editor, PendingText)
            assert editor.text == bad and message in editor.error
            assert persistence.storage[bridge.ledger_id] == baseline
            with manager.open_session(user_id=bridge.user_id, write_back=False) as session:
                assert session.ledger.graph.locals["effect_count"] == 0
                assert session.ledger.graph.locals["player_name"] == "Before"
            return [key(pygame.K_HOME), *[key(pygame.K_DELETE) for _ in bad],
                    text(good), key(pygame.K_RETURN)]
        assert draws[-1] is None
        return [pygame.event.Event(pygame.QUIT)]

    monkeypatch.setattr(client, "_next_events", events)
    args = argparse.Namespace(world=world.label, assets=None, scale=1,
                              reduced_motion=False, advance=0, screenshot=None)
    try:
        client._play(args, bridge, MusicPlayer())
        # A new Service owner reopens the ordinary saved JSON, not a model snapshot.
        assert isinstance(persistence.storage[bridge.ledger_id], str)
        with ServiceManager(persistence).open_session(
            user_id=bridge.user_id, write_back=False,
        ) as session:
            assert session.ledger.graph.locals["player_name"] == good
            assert session.ledger.graph.locals["effect_count"] == 1
            assert session.ledger.graph.locals["activation"] == {
                "operation": "rename", "kept": 7, "text": good,
            }
            assert session.ledger.choice_steps == 1
            assert len([record for record in session.ledger.output_stream.values()
                        if isinstance(record, ContentFragment) and record.content == "Named."]) == 1
        expected = [{"text": good}]
        if bad is not None and message != "required":
            expected.insert(0, {"text": bad})
        assert sent == expected  # no activation merge in the widget
    finally:
        bridge.close()
        pop_manual_world(world.label)


def test_native_completion_is_handled_while_text_has_focus(harness):
    from unittest.mock import Mock
    from tangl.pygame_client.voice import VoicePlayer

    bridge, choice, frame, calls, draws, focus, run = harness
    completion = pygame.event.Event(pygame.USEREVENT + 12)
    voice = Mock(spec=VoicePlayer)
    voice.handle_event.side_effect = lambda event: event is completion
    bridge.voice_player = voice
    run([[key(pygame.K_2), text("Dana"), completion], [key(pygame.K_RETURN)]])
    assert any(call.args[0] is completion for call in voice.handle_event.call_args_list)
    assert calls == [(choice.edge_id, {"text": "Dana"})]


def test_modal_does_not_pause_sprite_clock_or_turn_idle_into_a_busy_loop(tmp_path, monkeypatch):
    from tangl.presentation.sprite_sheet import SpriteSheetManifest
    from tangl.pygame_client.models import SheetSource, StageImage

    still, sheet = pygame.Surface((8, 8)), pygame.Surface((16, 8))
    still.fill("red")
    sheet.fill("red", (0, 0, 8, 8))
    sheet.fill("blue", (8, 0, 8, 8))
    still_path, sheet_path = tmp_path / "still.png", tmp_path / "sheet.png"
    pygame.image.save(still, str(still_path))
    pygame.image.save(sheet, str(sheet_path))
    manifest = SpriteSheetManifest.model_validate({
        "image": "sheet.png", "size": {"w": 16, "h": 8}, "canvas": {"w": 8, "h": 8},
        "frames": [{"rect": {"x": x, "y": 0, "w": 8, "h": 8}, "duration_ms": 100}
                   for x in (0, 8)],
    })
    choice = Choice(edge_id=uuid4(), text="Name", accepts=TextAccepts())
    turn = Turn(step=1, choices=[choice], images=[StageImage(
        role="avatar_im", source=str(still_path), clip="idle", timing="loop",
        sheets=(SheetSource(source=str(sheet_path), manifest=manifest),),
    )])
    now = [0]
    stage = Stage(clock=lambda: now[0], display_scale=1)
    stage.draw(turn)
    play = next(iter(stage._clips.values()))
    editor = PendingText(choice, (None, None, None), 1)
    now[0] = 150
    stage.draw(turn, editor)
    assert stage.animating and play.elapsed(now[0]) == 150
    assert play.started_ms == 0
    assert any(tuple(stage.surface.get_at((x, y)))[:3] == (0, 0, 95)
               for x in range(320) for y in range(184, 200))

    idle = Stage(display_scale=1)
    idle.draw(Turn(step=1, choices=[choice]), editor)
    assert not idle.animating  # a steady caret creates no animation timer
    waits = []
    monkeypatch.setattr(pygame.event, "wait", lambda *args: waits.append(args)
                        or pygame.event.Event(pygame.NOEVENT))
    monkeypatch.setattr(pygame.event, "get", lambda: [])
    client._next_events(idle)
    assert waits == [()]
