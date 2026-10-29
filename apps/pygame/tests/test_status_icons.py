"""Media-backed status is prepared once; fallback and rollover stay client-local."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest

pygame = pytest.importorskip("pygame")

from tangl.persistence import PersistenceManagerFactory
from tangl.presentation.hints import PresentationHints
from tangl.presentation.projection import ProjectedSection, ScalarValue
from tangl.pygame_client.__main__ import _frame
from tangl.pygame_client.bridge import PygameSessionBridge
from tangl.pygame_client.models import Turn
from tangl.pygame_client.stage import Stage
from tangl.service import ServiceManager
from tangl.service.world_registry import pop_manual_world, register_manual_world
from tangl.story import World

from pytest_helpers.status_icons import icon_world


@pytest.fixture
def status_world(tmp_path: Path) -> Iterator[World]:
    world = icon_world(tmp_path / "media")
    register_manual_world(world)
    yield world
    pop_manual_world(world.label)


def prepare(stage: Stage, bridge: PygameSessionBridge) -> None:
    stage.set_info(
        bridge.branding, bridge.status.sections, bridge.logo_source,
        status_available=bridge.status_available, session_id=bridge.ledger_id,
        icon_sources=bridge.status_icon_sources, world_id=bridge.world_id,
    )


def choose(bridge: PygameSessionBridge, text: str) -> None:
    with bridge.service_manager.open_session(user_id=bridge.user_id) as session:
        edge = next(edge for edge in session.ledger.cursor.edges_out() if edge.text == text)
    bridge.choose(edge.uid)


@pytest.mark.parametrize("size,zoom", [((320, 200), 3), ((640, 400), 2)])
def test_real_status_media_hover_and_revisits_are_cached_and_pure(
    status_world: World, size: tuple[int, int], zoom: int, monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bridge = PygameSessionBridge()
    media = Mock(wraps=bridge.service_manager.get_world_media)
    monkeypatch.setattr(bridge.service_manager, "get_world_media", media)
    load = Mock(wraps=pygame.image.load)
    monkeypatch.setattr(pygame.image, "load", load)
    envelope = bridge.start(status_world.label)
    frame = _frame(bridge, envelope)
    stage = Stage(logical_size=size, display_scale=zoom, animate=False)
    try:
        prepare(stage, bridge)
        token_draw = Mock(wraps=stage.chrome._icon)
        monkeypatch.setattr(stage.chrome, "_icon", token_draw)
        stage.draw(frame)
        assert media.call_count == load.call_count == 3
        assert not token_draw.called  # Explicit drawable media wins over all token suggestions.
        assert set(stage.chrome.icons) == {"pass.svg", "token.svg", "pouch.svg"}
        surfaces = dict(stage.chrome.icons)
        boxes = {identity: box for box, identity in stage.chrome.hitboxes}
        assert all(box.width == 12 * stage.density for box in boxes.values())
        assert all(stage.shell.get_rect().contains(box) for box in boxes.values())
        pass_pixels = stage.shell.subsurface(boxes["pass"])
        assert any(pass_pixels.get_at((x, y))[:3] == (40, 196, 219)
                   for x in range(pass_pixels.get_width()) for y in range(pass_pixels.get_height()))
        with bridge.service_manager.open_session(user_id=bridge.user_id) as session:
            before = session.ledger.unstructure()
        position = tuple(value * zoom for value in boxes["pass"].center)
        motion = pygame.event.Event(pygame.MOUSEMOTION, pos=position)
        assert stage.chrome.handle_event(motion, zoom)
        stage.draw(frame)
        assert stage.chrome.hover_text == "Hall pass\nCarried"
        assert stage.shell.get_rect().contains(stage.chrome.hover_box)
        pygame.image.save(stage.window, str(tmp_path / f"status-hover-{size[0]}.png"))
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position)
        assert stage.chrome.handle_event(click, zoom)
        assert stage.chrome.open and stage.chrome.selected_id == "pass"
        assert stage.chrome.hovered_id is None
        stage.chrome.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_TAB, mod=0,
        ), zoom)
        assert stage.chrome.selected_id == "token"
        stage.chrome.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0,
        ), zoom)
        for _ in range(3):
            bridge.refresh()
            prepare(stage, bridge)
            stage.chrome.handle_event(motion, zoom)
            stage.draw(frame, media_visibility={"portraits": False})
            stage.chrome.handle_event(pygame.event.Event(
                pygame.MOUSEMOTION, pos=(position[0], stage.chrome.height * zoom + 4),
            ), zoom)
            stage.draw(frame)
        assert media.call_count == load.call_count == 3
        assert stage.chrome.icons == surfaces
        with bridge.service_manager.open_session(user_id=bridge.user_id) as session:
            assert session.ledger.unstructure() == before
        choose(bridge, "Revisit")
        prepare(stage, bridge)
        stage.draw(frame)
        stage.chrome.handle_event(motion, zoom)
        assert stage.chrome.hovered_id == "pass"
        choose(bridge, "Leave the pass")
        prepare(stage, bridge)
        assert stage.chrome.hovered_id is None
        assert {section.section_id for section in bridge.status.sections} == {"token", "pouch"}
        choose(bridge, "Take the pass")
        prepare(stage, bridge)
        assert stage.chrome.icons == surfaces
        assert media.call_count == load.call_count == 3
    finally:
        pygame.quit()


@pytest.mark.parametrize("ref,token,short,expected", [
    ("missing.svg", "key", "HP", None),
    ("bad.svg", "key", "HP", None),
    ("notes.txt", "key", "HP", None),
    ("unfetched.svg", "key", "HP", None),
    ("bad.svg", "unknown-token", "HP", "HP"),
    ("missing.svg", "unknown-token", None, "Hall pass: Carried"),
    (None, "pass.svg", "HP", "HP"),
])
@pytest.mark.parametrize("size", [(320, 200), (640, 400)])
def test_missing_bad_unsupported_and_unfetched_media_follow_cached_fallbacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ref: str | None, token: str, short: str | None, expected: str | None,
    size: tuple[int, int],
) -> None:
    (tmp_path / "bad.svg").write_text("not an SVG", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("Not an image", encoding="utf-8")
    (tmp_path / "unfetched.svg").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 1234\n",
        encoding="utf-8",
    )
    world = icon_world(tmp_path, pass_hints=PresentationHints(
        icon_media=ref, icon=token, short_label=short, icon_only=True,
    ))
    register_manual_world(world)
    bridge = PygameSessionBridge()
    media = Mock(wraps=bridge.service_manager.get_world_media)
    monkeypatch.setattr(bridge.service_manager, "get_world_media", media)
    load = Mock(wraps=pygame.image.load)
    monkeypatch.setattr(pygame.image, "load", load)
    bridge.start(world.label)
    stage = Stage(logical_size=size, display_scale=1)
    try:
        prepare(stage, bridge)
        stage.chrome.font = Mock(wraps=stage.chrome.font)
        draw_token = Mock(wraps=stage.chrome._icon)
        monkeypatch.setattr(stage.chrome, "_icon", draw_token)
        stage.draw(Turn(step=1))
        assert ref not in stage.chrome.icons
        assert any(call.args[1] == token for call in draw_token.call_args_list)
        if expected is None:
            assert stage.chrome._entry_width(bridge.status.sections[0]) == 12 * stage.density
        else:
            rendered = [call.args[0] for call in stage.chrome.font.render.call_args_list]
            if short:
                assert expected in rendered
            else:
                assert any(text.startswith("Hall pass") for text in rendered)
        box = next(box for box, identity in stage.chrome.hitboxes if identity == "pass")
        stage.chrome.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=box.center), 1)
        stage.draw(Turn(step=1))
        assert stage.chrome.hover_text == "Hall pass\nCarried"
        calls = media.call_count, load.call_count
        for _ in range(2):
            choose(bridge, "Revisit")
            prepare(stage, bridge)
            stage.draw(Turn(step=2))
        assert (media.call_count, load.call_count) == calls
        assert bridge.status.sections[0].title == "Hall pass"
        assert bridge.status.sections[0].value.value == "Carried"
        if ref is None:
            assert all(call.kwargs["media"] != "pass.svg" for call in media.call_args_list)
    finally:
        pop_manual_world(world.label)
        pygame.quit()


def test_drawable_icon_with_text_advice_keeps_full_readable_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = icon_world(tmp_path, pass_hints=PresentationHints(
        icon_media="pass.svg", icon="key", short_label="HP", icon_only=False,
    ))
    register_manual_world(world)
    bridge = PygameSessionBridge()
    bridge.start(world.label)
    stage = Stage(display_scale=1)
    try:
        prepare(stage, bridge)
        stage.chrome.font = Mock(wraps=stage.chrome.font)
        stage.draw(Turn(step=1))
        assert "pass.svg" in stage.chrome.icons
        rendered = [call.args[0] for call in stage.chrome.font.render.call_args_list]
        assert any(text.startswith("Hall pass") for text in rendered)
        assert "HP" not in rendered
    finally:
        pop_manual_world(world.label)
        pygame.quit()


def test_changed_reference_and_same_name_in_another_world_resolve_independently(
    status_world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_root = tmp_path / "other"
    other_root.mkdir()
    (other_root / "replacement.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24">'
        '<rect width="24" height="24" fill="blue"/></svg>', encoding="utf-8",
    )
    other = icon_world(other_root, label="other_status_icons")
    # Same local coordinate, genuinely different art in another world inventory.
    path = other.resources.get_rit("pass.svg").path
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24">'
                    '<rect width="24" height="24" fill="red"/></svg>', encoding="utf-8")
    register_manual_world(other)
    bridge = PygameSessionBridge()
    media = Mock(wraps=bridge.service_manager.get_world_media)
    monkeypatch.setattr(bridge.service_manager, "get_world_media", media)
    bridge.start(status_world.label)
    stage = Stage(display_scale=1)
    try:
        prepare(stage, bridge)
        first = stage.chrome.icons["pass.svg"]
        stage.draw(Turn(step=1))
        box = stage.chrome.hitboxes[0][0]
        stage.chrome.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=box.center), 1)
        bridge.start(other.label)
        prepare(stage, bridge)
        assert stage.chrome.hovered_id is None
        second = stage.chrome.icons["pass.svg"]
        assert second is not first
        assert second.get_at((4, 4))[:3] == (255, 0, 0)
        assert media.call_count == 6
        with bridge.service_manager.open_session(user_id=bridge.user_id, write_back=True) as session:
            session.ledger.graph.locals["item_hints"]["pass"]["icon_media"] = "replacement.svg"
        choose(bridge, "Revisit")
        prepare(stage, bridge)
        assert bridge.status.sections[0].hints.icon_media == "replacement.svg"
        assert stage.chrome.icons["replacement.svg"].get_at((4, 4))[:3] == (0, 0, 255)
        assert media.call_count == 7
        bridge.start(status_world.label)
        prepare(stage, bridge)
        assert stage.chrome.icons["pass.svg"] is first
        assert media.call_count == 7
    finally:
        pop_manual_world(other.label)
        pygame.quit()


@pytest.mark.parametrize("size,zoom", [((320, 200), 3), ((640, 400), 1)])
def test_hover_clears_for_overflow_channel_and_session_and_keeps_details(
    size: tuple[int, int], zoom: int,
) -> None:
    stage = Stage(logical_size=size, display_scale=zoom)
    entries = [ProjectedSection(
        section_id=str(index), title=f"Long full item label {index}",
        value=ScalarValue(value="Current readable value " * 20),
        hints=PresentationHints(short_label=f"I{index}", icon_only=True),
    ) for index in range(18)]
    try:
        stage.set_info(None, entries, None, status_available=True)
        stage.draw(Turn(step=1))
        chrome = stage.chrome
        box = chrome.hitboxes[0][0]
        chrome.handle_event(pygame.event.Event(
            pygame.MOUSEMOTION, pos=tuple(value * zoom for value in box.center),
        ), zoom)
        stage.draw(Turn(step=1))
        assert chrome.hover_text.startswith("Long full item label 0\nCurrent readable value")
        assert stage.shell.get_rect().contains(chrome.hover_box)
        chrome.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=tuple(value * zoom for value in chrome.next_box.center),
        ), zoom)
        assert chrome.hovered_id is None and not chrome.hitboxes
        stage.draw(Turn(step=1))
        chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, mod=pygame.KMOD_CTRL), zoom)
        assert chrome.open
        chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0), zoom)
        assert chrome.selected_id == "1"
        stage.set_info(None, [], None, status_available=False)
        assert stage.chrome is None
        stage.set_info(None, entries, None, status_available=True, session_id=uuid4())
        assert stage.chrome.hovered_id is None and not stage.chrome.open
        stage.draw(Turn(step=1))
        chrome = stage.chrome
        box = chrome.hitboxes[0][0]
        chrome.handle_event(pygame.event.Event(
            pygame.MOUSEMOTION, pos=tuple(value * zoom for value in box.center),
        ), zoom)
        assert chrome.hovered_id is not None
        stage.set_info(None, entries, None, status_available=True,
                       session_id=stage._info_session, world_id="another-world")
        assert stage.chrome.hovered_id is None
    finally:
        pygame.quit()


def test_hints_survive_dto_and_owner_graph_json(status_world: World, tmp_path: Path) -> None:
    storage = tmp_path / "store"
    manager = ServiceManager(PersistenceManagerFactory.json_file(base_path=storage))
    bridge = PygameSessionBridge(service_manager=manager)
    bridge.start(status_world.label)
    with manager.open_session(user_id=bridge.user_id, write_back=True) as session:
        graph = session.ledger.graph
        expected = bridge.status.sections[0].hints
        owner_id = session.ledger.cursor_id
        graph.get(owner_id).content_hints = expected
    reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=storage))
    with reopened.open_session(user_id=bridge.user_id) as session:
        restored = session.ledger.graph
        assert restored is not graph
        assert session.ledger.cursor_id == owner_id
        assert restored.get(owner_id).content_hints == expected
        assert restored.locals["item_hints"]["pass"]["icon_media"] == "pass.svg"
    dto = reopened.get_story_info(user_id=bridge.user_id, channels=["ui-status"]).to_dto()
    assert dto["sections"][0]["title"] == "Hall pass"
    assert dto["sections"][0]["hints"]["icon_media"] == "pass.svg"
    assert dto["sections"][0]["hints"]["short_label"] == "HP"


def test_runnable_client_hover_and_keyboard_inspection_do_not_submit_or_fetch(
    status_world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.pygame_client import __main__ as client

    reads: list[tuple[str, str]] = []
    active: list[PygameSessionBridge] = []
    original = PygameSessionBridge._world_image_source

    def read(bridge: PygameSessionBridge, world_id: str, media: str) -> str | None:
        active[:] = [bridge]
        reads.append((world_id, media))
        return original(bridge, world_id, media)

    monkeypatch.setattr(PygameSessionBridge, "_world_image_source", read)
    commit = Mock(side_effect=AssertionError("Inspection submitted a game action"))
    monkeypatch.setattr(PygameSessionBridge, "choose", commit)
    load = Mock(wraps=pygame.image.load)
    monkeypatch.setattr(pygame.image, "load", load)
    batch = 0
    before = None

    def events(stage: Stage) -> list[pygame.event.Event]:
        nonlocal batch, before
        batch += 1
        bridge = active[0]
        if batch == 1:
            with bridge.service_manager.open_session(user_id=bridge.user_id) as session:
                before = session.ledger.unstructure()
            box = next(box for box, identity in stage.chrome.hitboxes if identity == "pass")
            return [pygame.event.Event(pygame.MOUSEMOTION,
                                       pos=tuple(value * 2 for value in box.center))]
        if batch == 2:
            assert stage.chrome.hover_text == "Hall pass\nCarried"
            assert stage.shell.get_rect().contains(stage.chrome.hover_box)
            return [pygame.event.Event(pygame.WINDOWLEAVE)]
        if batch == 3:
            assert stage.chrome.hovered_id is None
            return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, mod=pygame.KMOD_CTRL)]
        if batch == 4:
            assert stage.chrome.open
            return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0)]
        assert stage.chrome.selected_id == "token"
        with bridge.service_manager.open_session(user_id=bridge.user_id) as session:
            assert session.ledger.unstructure() == before
        assert len(reads) == load.call_count == 3
        return [pygame.event.Event(pygame.QUIT)]

    monkeypatch.setattr(client, "_next_events", events)
    assert client.main(["--world", status_world.label, "--scale", "2"]) == 0
    assert not commit.called
