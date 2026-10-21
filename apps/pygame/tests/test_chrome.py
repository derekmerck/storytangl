"""Compact disclosed status, freshness, pure inspection and shell coordinates."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest

pygame = pytest.importorskip("pygame")

from tangl.core import EntityTemplate, Selector, Token
from tangl.mechanics.sandbox import (
    ChargeFacet, SandboxCompiledAssetType, SandboxLocation, SandboxMap, SandboxScope,
)
from tangl.mechanics.sandbox.compact_status import advertise_compact_status, project_compact_status
from tangl.presentation.hints import PresentationHints
from tangl.presentation.projection import (
    BrandingValue, InfoAffordance, ProjectedSection, ProjectionRequest, ScalarValue,
)
from tangl.presentation.surface import HasSurface, Surface
from tangl.pygame_client.bridge import PygameSessionBridge
from tangl.pygame_client.chrome import section_text
from tangl.pygame_client.models import Choice, Commit, Line, Turn
from tangl.pygame_client.stage import Stage
from tangl.service import ServiceManager
from tangl.service.media import MediaContentProfile, MediaRenderProfile
from tangl.service.response import JsonValue, RuntimeEnvelope
from tangl.service.world_registry import pop_manual_world, register_manual_world
from tangl.story import Block, StoryGraph, World
from tangl.vm.runtime.frame import PhaseCtx


def section(label: str, value: str) -> dict[str, object]:
    return {"section_id": label, "title": label, "value": {"value_type": "scalar", "value": value}}


class HudAssetType(SandboxCompiledAssetType):
    """Fixture-owned catalog that never clears another world's asset singletons."""


class HudLocation(HasSurface, SandboxLocation):
    """Witness location can also disclose an ordinary document surface."""


@pytest.fixture
def hud_world(tmp_path: Path) -> Iterator[World]:
    from tangl.media.media_resource.resource_manager import ResourceManager

    logo = tmp_path / "logo.svg"
    logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
                    '<rect width="20" height="20" fill="teal"/></svg>')
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    world = World.from_script_data(script_data={
        "label": "compact_hud_witness",
        "metadata": {"title": "Workshop", "start_at": "workshop.menu",
                     "branding": {"name": "The Workshop", "logo_media": "logo.svg"}},
        "scenes": {
            "workshop": {"kind": SandboxScope, "locals": {
                "world_turn": 3, "period_icons": {1: "sun", 2: "sun", 3: "sunset", 4: "moon"},
            }, "blocks": {"menu": {
                "kind": HudLocation, "location_name": "Workshop", "content": "Ready to work.",
                "scheduled_events": [{"label": "Visit the study", "target": "errand",
                                      "return_to_location": True}],
            }}},
            "errand": {"title": "The Study", "locals": {"exit_time_cost": {"duration": 1}},
                       "blocks": {
                "first": {"content": "A two-part errand.",
                          "actions": [{"text": "Continue", "successor": "errand.second"}]},
                "second": {"content": "The second part of the errand.",
                           "actions": [{"text": "Finish", "successor": "errand.done"}]},
                "done": {"content": "The errand is complete."},
            }},
        },
    }, resources=resources)
    # Author both scenes into one shared scope before template materialization.
    world.find_template("workshop").add_child(world.find_template("errand"))
    world.dispatch.register(advertise_compact_status, task="advertise_story_info_channels",
                            wants_caller_kind=Block, wants_exact_kind=False)
    world.dispatch.register(project_compact_status, task="get_story_info",
                            wants_caller_kind=Block, wants_exact_kind=False)

    def supply_items(*, caller: StoryGraph, ctx: PhaseCtx, **_kw: object) -> None:
        scope = caller.find_one(Selector(has_kind=SandboxScope))
        if scope.player_assets.assets:
            return
        for label in ("lamp", "key", "bag"):
            if HudAssetType.get_instance(f"hud_{label}") is None:
                HudAssetType(label=f"hud_{label}", name=label.title(), portable=True,
                             lit=label == "lamp",
                             charge=ChargeFacet(current=3, maximum=3) if label == "lamp" else None)
            asset = EntityTemplate.compile({
                "kind": Token[HudAssetType], "label": label,
                "token_from": f"hud_{label}",
            }).materialize()
            ctx.graph.add(asset)
            scope.player_assets.add_asset(asset)

    world.dispatch.register(supply_items, task="story_ready",
                            wants_caller_kind=StoryGraph, wants_exact_kind=False)
    register_manual_world(world)
    yield world
    pop_manual_world(world.label)
    HudAssetType.clear_instances()


def values(bridge: PygameSessionBridge) -> dict[str, str]:
    return {s.section_id: section_text(s) for s in bridge.status.sections}


def pick(bridge: PygameSessionBridge, text: str) -> RuntimeEnvelope:
    turns = bridge.build_turns(list(bridge.refresh().fragments))
    edge_id = next(choice.edge_id for choice in turns[-1].choices if choice.text == text)
    return bridge.choose(edge_id)


def test_service_sandbox_status_survives_called_scene_and_return(hud_world: World) -> None:
    bridge = PygameSessionBridge()
    opening = bridge.start(hud_world.label)
    assert set(values(bridge)) == {"scene", "period", "day", "item:bag", "item:key", "item:lamp"}
    assert values(bridge)["day"] == "Day 1"
    assert values(bridge)["item:lamp"] == "lit, 3 charges"
    assert bridge.branding.name == "The Workshop"
    assert Path(bridge.logo_source).name == "logo.svg"
    pick(bridge, "Visit the study")
    assert values(bridge)["scene"] == "The Study"
    assert "ui-status" in bridge._available_info
    pick(bridge, "Continue")
    assert values(bridge)["scene"] == "The Study"
    assert "ui-status" in bridge._available_info
    second = pick(bridge, "Finish")
    assert values(bridge)["scene"] == "Workshop"
    # Ordinary terminal return restores the menu without a status-specific origin cache.
    assert second.fragments
    assert values(bridge)["day"] == "Day 2"
    assert values(bridge)["period"] == "morning"
    assert values(bridge)["item:lamp"] == "lit, 2 charges"
    assert opening.metadata["ledger_id"] == second.metadata["ledger_id"]
    pick(bridge, "Drop Bag")
    assert "item:bag" not in values(bridge)


def test_scoped_overrides_and_explicit_absence(hud_world: World) -> None:
    bridge = PygameSessionBridge()
    bridge.start(hud_world.label)
    with bridge.service_manager.open_session(user_id=bridge.user_id, write_back=True) as session:
        caller = session.ledger.cursor
        caller.parent.locals["ui_status"] = [section("scene-override", "Scope status")]
        caller.locals["ui_status"] = [section("block-override", "Local status")]
    projected = bridge.service_manager.get_story_info(
        user_id=bridge.user_id, channels=["ui-status"],
    )
    assert [s.section_id for s in projected.sections] == ["block-override"]
    with bridge.service_manager.open_session(user_id=bridge.user_id, write_back=True) as session:
        del session.ledger.cursor.locals["ui_status"]
    projected = bridge.service_manager.get_story_info(
        user_id=bridge.user_id, channels=["ui-status"],
    )
    assert [s.section_id for s in projected.sections] == ["scene-override"]
    with bridge.service_manager.open_session(user_id=bridge.user_id, write_back=True) as session:
        session.ledger.cursor.locals["ui_status"] = None
    assert bridge.service_manager.get_story_info(user_id=bridge.user_id,
                                                 channels=["ui-status"]).sections == []


def test_status_queries_are_pure_and_cached_by_dirty_version(
    hud_world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.pygame_client.__main__ import _frame

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    hud_world.metadata["ui_preferences"] = [
        {"id": "extra", "kind": "boolean", "label": "Optional detail", "default": True},
    ]
    bridge = PygameSessionBridge()
    read = Mock(wraps=bridge.service_manager.get_story_info)
    branding = Mock(wraps=bridge.service_manager.get_world_info)
    monkeypatch.setattr(bridge.service_manager, "get_story_info", read)
    monkeypatch.setattr(bridge.service_manager, "get_world_info", branding)
    envelope = bridge.start(hud_world.label)
    assert read.call_count == 1  # InfoState advertises exact ids; only fetch selected status.
    assert branding.call_count == 2  # Shared public catalog and branding projection.
    bridge.discover_preferences(hud_world.label)
    assert branding.call_count == 3  # One exact preference read, not another catalog.
    with bridge.service_manager.open_session(user_id=bridge.user_id) as session:
        before = session.ledger.unstructure()
        scope = session.ledger.graph.find_one(Selector(has_kind=SandboxScope))
        inventory = {label: token.uid for label, token in scope.player_assets.assets.items()}
    stage = Stage(chrome=True)
    try:
        for _ in range(3):
            bridge._sync(envelope)
            bridge.refresh()
            frame = _frame(bridge, envelope)
            stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source)
            stage.draw(frame)
            stage.chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i,
                                                         mod=pygame.KMOD_CTRL), 3)
            stage.draw(frame)
            bridge.cycle_preference("extra")
    finally:
        pygame.quit()
    assert read.call_count == 1 and branding.call_count == 3
    with bridge.service_manager.open_session(user_id=bridge.user_id) as session:
        assert session.ledger.unstructure() == before
        scope = session.ledger.graph.find_one(Selector(has_kind=SandboxScope))
        after_inventory = {label: token.uid for label, token in scope.player_assets.assets.items()}
        assert after_inventory == inventory
    # Equal numeric versions still process channel removal and reappearance.
    marker = envelope.metadata["info_state"]
    removed = envelope.model_copy(update={"metadata": {
        **envelope.metadata, "info_state": {**marker, "available_channels": []},
    }})
    bridge._sync(removed)
    assert not bridge.status.sections and read.call_count == 1
    bridge._sync(envelope)
    assert bridge.status.sections and read.call_count == 2
    # A new story at the same step is not an unchanged version.
    fresh = bridge.start(hud_world.label)
    assert fresh.step == envelope.step
    assert read.call_count == 3 and branding.call_count == 3
    pick(bridge, "Wait")
    assert read.call_count == 4
    assert values(bridge)["day"] == "Day 2"
    bridge.refresh()
    assert read.call_count == 4


def test_world_switch_at_equal_step_clears_status_and_reuses_only_public_branding(
    hud_world: World,
) -> None:
    empty = World.from_script_data(script_data={
        "label": "empty_hud_world", "metadata": {"title": "A quiet world"},
        "scenes": {"quiet": {"blocks": {"start": {"content": "No status provider."}}}},
    })
    register_manual_world(empty)
    try:
        bridge = PygameSessionBridge()
        first = bridge.start(hud_world.label)
        second = bridge.start(empty.label)
        assert first.step == second.step
        assert not bridge.status.sections and bridge.logo_source is None
        assert bridge.branding.name == "A quiet world"
        bridge.start(hud_world.label)
        assert "item:lamp" in values(bridge)
        assert bridge.branding.name == "The Workshop"
    finally:
        pop_manual_world(empty.label)


@pytest.mark.parametrize("override", [[], [section("block", "Block wins")]])
def test_world_scene_block_status_precedence_during_real_call(
    hud_world: World, override: list[dict[str, object]],
) -> None:
    hud_world.locals["ui_status"] = [section("world", "World default")]
    hud_world.find_template("errand").payload.locals["ui_status"] = [section("scene", "Scene wins")]
    hud_world.find_template("errand.first").payload.locals = {"ui_status": override}
    bridge = PygameSessionBridge()
    bridge.start(hud_world.label)
    assert values(bridge) == {"world": "World default"}
    pick(bridge, "Visit the study")
    assert values(bridge) == ({"block": "Block wins"} if override else {})
    assert "ui-status" in bridge._available_info
    pick(bridge, "Continue")
    assert values(bridge) == {"scene": "Scene wins"}
    pick(bridge, "Finish")
    assert values(bridge) == {"world": "World default"}


def test_first_status_projection_does_not_mutate_the_session(hud_world: World) -> None:
    bridge = PygameSessionBridge()
    user = bridge.service_manager.create_user(secret="hud-purity")
    user_id = user.details["user_id"]
    bridge.service_manager.create_story(user_id=user_id, world_id=hud_world.label)
    with bridge.service_manager.open_session(user_id=user_id) as session:
        before = session.ledger.unstructure()
        scope = session.ledger.graph.find_one(Selector(has_kind=SandboxScope))
        inventory = {label: token.uid for label, token in scope.player_assets.assets.items()}
    bridge.service_manager.get_story_info(user_id=user_id, channels=["ui-status"])
    with bridge.service_manager.open_session(user_id=user_id) as session:
        assert session.ledger.unstructure() == before
        scope = session.ledger.graph.find_one(Selector(has_kind=SandboxScope))
        after_inventory = {label: token.uid for label, token in scope.player_assets.assets.items()}
        assert after_inventory == inventory


def test_envelope_availability_has_exact_catalog_ids_including_geometry(hud_world: World) -> None:
    import tangl.mechanics.surface_story_info  # noqa: F401 -- explicit world composition

    menu = hud_world.find_template("workshop.menu").payload
    menu.map = SandboxMap(name="workshop-map", plate="optional.svg")
    menu.surface = Surface(name="workbench")
    bridge = PygameSessionBridge()
    envelope = bridge.start(hud_world.label)
    catalog = bridge.service_manager.get_story_info(user_id=bridge.user_id)
    expected = {channel.channel_id for channel in catalog.channels}
    assert set(envelope.metadata["info_state"]["available_channels"]) == expected
    assert {"ui-status", "ui-map-plate", "ui-surface"} <= expected
    assert bridge.map_plate().name == "workshop-map"
    assert bridge.surface().name == "workbench"


def test_detail_wrap_preserves_words_and_splits_only_oversized_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.pygame_client.chrome import wrap_pixels

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(chrome=True)
    try:
        font = stage.font
        width = font.size("one two")[0]
        assert wrap_pixels(font, "one two three", width) == ["one two", "three"]
        token = "W" * 120
        lines = wrap_pixels(font, token, width)
        assert "".join(lines) == token
        assert all(font.size(line)[0] <= width for line in lines)
    finally:
        pygame.quit()


def test_non_sandbox_custom_provider_uses_the_same_channel_and_scoped_namespace() -> None:
    from tangl.presentation.projection import ProjectedState

    world = World.from_script_data(script_data={
        "label": "custom_compact_status", "locals": {"ui_status": [
            {**section("calendar", "24 Brumaire"), "hints": {"icon": "alien-calendar"}},
            {**section("phase", "Fifth watch"), "hints": {"icon": "unknown-phase"}},
        ]},
        "scenes": {"intro": {"blocks": {
            "start": {"content": "No sandbox, clock or inventory.",
                      "actions": [{"text": "Next", "successor": "intro.next"}]},
            "next": {"content": "An explicitly empty local status.", "locals": {"ui_status": []}},
        }}},
    })

    def advertise(**_kw: object) -> list[InfoAffordance]:
        return [InfoAffordance(channel_id="ui-status", label="Local status")]

    def project(
        *, ctx: PhaseCtx, request: ProjectionRequest, **_kw: object,
    ) -> list[ProjectedSection]:
        if "ui-status" in request.requested_channels():
            return ProjectedState.model_validate({"sections": ctx.get_ns()["ui_status"]}).sections
        return []

    world.dispatch.register(advertise, task="advertise_story_info_channels")
    world.dispatch.register(project, task="get_story_info")
    register_manual_world(world)
    try:
        bridge = PygameSessionBridge()
        bridge.start(world.label)
        assert values(bridge) == {"calendar": "24 Brumaire", "phase": "Fifth watch"}
        pick(bridge, "Next")
        assert not bridge.status.sections
        assert bridge.branding.name == world.label
    finally:
        pop_manual_world(world.label)


@pytest.mark.parametrize("mode", ["missing", "pointer", "url", "inline", "decoder"])
def test_logo_uses_normal_profiles_and_unavailable_media_falls_back_to_name(
    hud_world: World, mode: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    if mode == "missing":
        hud_world.metadata["branding"]["logo_media"] = "absent.svg"
    elif mode in ("pointer", "decoder"):
        path = hud_world.resources.get_rit("logo.svg").path
        path.write_text("version https://git-lfs.github.com/spec/v1\n" if mode == "pointer"
                        else "This is not an SVG image")
    profile = MediaContentProfile.PASSTHROUGH
    if mode == "url":
        profile = MediaContentProfile.MEDIA_SERVER
    elif mode == "inline":
        profile = MediaContentProfile.INLINE_DATA
    bridge = PygameSessionBridge(media_render_profile=MediaRenderProfile(content_profile=profile))
    bridge.start(hud_world.label)
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(chrome=True)
    try:
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source)
        stage.draw(Turn(step=1))
        assert stage.chrome.branding.name == "The Workshop"
        assert stage.chrome.logo is None
    finally:
        pygame.quit()


def test_long_compact_labels_use_bounded_measurement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(chrome=True)
    try:
        chrome = stage.chrome
        font = Mock(wraps=chrome.font)
        chrome.font = font
        clipped = chrome._clip("Long label " * 10000, 90)
        assert clipped.endswith("...")
        assert font.size(clipped)[0] <= 90
        assert font.size.call_count < 25
    finally:
        pygame.quit()


@pytest.mark.parametrize("size,scale", [((320, 200), 2), ((640, 400), 1)])
def test_render_service_backed_compact_status_layout(
    hud_world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    size: tuple[int, int], scale: int,
) -> None:
    from tangl.pygame_client.__main__ import _frame

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    bridge = PygameSessionBridge()
    envelope = bridge.start(hud_world.label)
    stage = Stage(logical_size=size, display_scale=scale, chrome=True, animate=False)
    try:
        frame = _frame(bridge, envelope)
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source)
        stage.draw(frame)
        assert stage.chrome.logo is not None
        pygame.image.save(stage.window, str(tmp_path / f"hud-{size[0]}x{size[1]}.png"))
        stage.chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i,
                                                     mod=pygame.KMOD_CTRL), scale)
        stage.draw(frame)
        pygame.image.save(stage.window, str(tmp_path / f"hud-details-{size[0]}x{size[1]}.png"))
    finally:
        pygame.quit()


def test_main_details_capture_input_without_choices_and_preserve_music_shortcuts(
    hud_world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.pygame_client import __main__ as client
    from tangl.pygame_client.music import MusicPlayer

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    committed: list[tuple[UUID, JsonValue | None]] = []
    expected: list[tuple[UUID, JsonValue | None]] = []
    original = PygameSessionBridge.choose

    def choose(bridge: PygameSessionBridge, edge_id: UUID,
               payload: JsonValue | None = None) -> RuntimeEnvelope:
        committed.append((edge_id, payload))
        return original(bridge, edge_id, payload)

    monkeypatch.setattr(PygameSessionBridge, "choose", choose)
    muted = Mock()
    monkeypatch.setattr(MusicPlayer, "toggle_mute", muted)
    batch = 0

    def key(code: int, mod: int = 0) -> pygame.event.Event:
        return pygame.event.Event(pygame.KEYDOWN, key=code, mod=mod, unicode="")

    def events(stage: Stage) -> list[pygame.event.Event]:
        nonlocal batch
        batch += 1
        if batch == 1:
            choice = next(action for _box, action in stage.hitboxes if isinstance(action, Commit))
            expected.append((choice.edge_id, choice.payload))
            return [key(pygame.K_i, pygame.KMOD_CTRL)]
        if batch == 2:
            assert stage.chrome.open and not committed
            return [key(pygame.K_1), key(pygame.K_m, pygame.KMOD_CTRL)]
        if batch == 3:
            assert stage.chrome.open and not committed
            box, _action = next((box, action) for box, action in stage.hitboxes
                                if isinstance(action, Commit))
            return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                       pos=stage.window_point(box.center))]
        if batch == 4:
            assert not stage.chrome.open and not committed
            return [key(pygame.K_1)]
        assert committed
        return [pygame.event.Event(pygame.QUIT)]

    monkeypatch.setattr(client, "_next_events", events)
    assert client.main(["--world", hud_world.label, "--scale", "1"]) == 0
    assert committed == expected
    muted.assert_called_once()


def test_status_clicks_keep_identity_when_entries_change_before_redraw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(chrome=True, display_scale=1)
    entries = [ProjectedSection(**section("a", "First")),
               ProjectedSection(**section("b", "Second"))]
    brand = BrandingValue(name="Identity witness")
    try:
        stage.set_info(brand, entries, None)
        stage.draw(Turn(step=1))
        boxes = [box for box, _entry in stage.chrome.hitboxes]
        stage.set_info(brand, list(reversed(entries)), None)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boxes[0].center)
        assert stage.chrome.handle_event(click, 1)
        assert stage.chrome.selected_id == "a"
        stage.set_info(brand, [entries[1]], None)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boxes[1].center)
        assert stage.chrome.handle_event(click, 1)
        assert stage.chrome.selected_id == "b"
        stage.set_info(brand, [], None)
        assert stage.chrome.handle_event(click, 1)
        assert not stage.chrome.open
    finally:
        pygame.quit()


@pytest.mark.parametrize("size,scale", [((320, 200), 3), ((640, 400), 1)])
def test_shell_keeps_world_surface_and_choice_coordinates(
    size: tuple[int, int], scale: int, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import uuid4

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(logical_size=size, display_scale=scale, chrome=True)
    turn = Turn(step=1, lines=[Line(text="A readable passage.")],
                choices=[Choice(edge_id=uuid4(), text="Continue", available=True)])
    stage.set_info(BrandingValue(name="A world"), [
        ProjectedSection(**section(f"Entry {i}", "Long status " * 300),
                         hints=PresentationHints(icon="unknown-icon")) for i in range(9)
    ], None)
    stage.draw(turn)
    assert stage.surface.get_size() == size
    assert stage.window.get_size() == (size[0] * scale,
                                       (size[1] + stage.chrome_height) * scale)
    box, action = next((box, action) for box, action in stage.hitboxes
                        if isinstance(action, Commit))
    screen = (box.centerx * scale, (box.centery + stage.chrome_height) * scale)
    assert stage.hit(screen) == action
    assert stage.hit((box.centerx * scale, 2 * scale)) is None
    entry, _index = stage.chrome.hitboxes[0]
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                               pos=(entry.centerx * scale, entry.centery * scale))
    assert stage.chrome.handle_event(click, scale)
    assert stage.chrome.open and stage.chrome.selected_id == "Entry 0"
    stage.chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0), scale)
    stage.chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i,
                                                 mod=pygame.KMOD_CTRL), scale)
    stage.draw(turn)
    assert stage.chrome.open
    for _ in range(7):
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0)
        stage.chrome.handle_event(event, scale)
    stage.draw(turn)
    assert stage.chrome.selected_id == "Entry 7" and stage.chrome.page == 1
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN, mod=0)
    stage.chrome.handle_event(event, scale)
    stage.draw(turn)
    assert stage.chrome.detail_page == 1
    stage.chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0), scale)
    assert not stage.chrome.open and stage.hit(screen) == action
    pygame.quit()
