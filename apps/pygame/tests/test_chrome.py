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
from tangl.journal.fragments import AttributedFragment, ChoiceFragment, ContentFragment
from tangl.presentation.hints import PresentationHints
from tangl.presentation.projection import (
    BrandingValue, InfoAffordance, ProjectedSection, ProjectionRequest, ScalarValue,
)
from tangl.presentation.surface import HasSurface, Surface
from tangl.pygame_client.bridge import PygameSessionBridge
from tangl.pygame_client.chrome import BAR, SELECTED, section_text
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
                "world_turn": 3,
                "period_icons": {"1": "sun", "2": "sun", "3": "sunset", "4": "moon"},
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
                HudAssetType(label=f"hud_{label}", name=label.title(), portable=True, icon=label,
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


def test_a_line_that_only_restates_the_status_is_left_to_the_bar(hud_world: World) -> None:
    # A world tags a line that says what the status says, `status:<section_id>`.
    # This bar shows the scene and the day, so those lines are the bar's alone,
    # narration or a speaker's. A line that names a section the bar does not
    # show, or no section, is the reader's, and in a world with no status bar,
    # every line is.
    said = [("**Workshop**", ["status:scene"]), ("Day 1, morning.", ["status:day", "status:period"]),
            ("Ready to work.", []), ("Rain later.", ["status:day", "status:weather"])]
    spoken = AttributedFragment(content="Welcome to the Workshop.", who="Guide", how="", media="",
                                hints=PresentationHints(style_tags=["status:scene"]))

    def read(bridge: PygameSessionBridge) -> list[str]:
        fragments = [ContentFragment(content=text,
                                     hints=PresentationHints(style_tags=tags) if tags else None)
                     for text, tags in said]
        turns = bridge.build_turns([*fragments, spoken])
        return [line.text for turn in turns for line in turn.lines]

    bridge = PygameSessionBridge()
    bridge.start(hud_world.label)
    assert read(bridge) == ["Ready to work.", "Rain later."]
    plain = World.from_script_data(script_data={
        "label": "no_status_bar", "scenes": {"intro": {"blocks": {"start": {"content": "Hi."}}}},
    })
    register_manual_world(plain)
    try:
        elsewhere = PygameSessionBridge()
        elsewhere.start(plain.label)
        assert read(elsewhere) == [*(text for text, _ in said), "Welcome to the Workshop."]
    finally:
        pop_manual_world(plain.label)


def test_a_dropped_status_line_leaves_no_page_to_turn_to(hud_world: World) -> None:
    # Narration, then a menu whose only text is the day the bar already shows:
    # the reader reads the narration and acts there, with no blank page between.
    from tangl.pygame_client.__main__ import _frame
    from tangl.pygame_client.presentation import visual_passages

    bridge = PygameSessionBridge()
    bridge.start(hud_world.label)
    envelope = RuntimeEnvelope(fragments=[
        ContentFragment(content="The errand ends.", step=1),
        ContentFragment(content="Day 1, morning.", step=2,
                        hints=PresentationHints(style_tags=["status:day", "status:period"])),
        ChoiceFragment(text="Visit the study", edge_id=UUID(int=1), step=2),
    ])
    stage = Stage(logical_size=(320, 200), display_scale=1)
    stage.paged = True
    stage.present(_frame(bridge, envelope), visual_passages(bridge, envelope))
    assert [[row.text for row in page.rows] for page in stage.pages] == [["The errand ends."]]
    assert stage.choices_ready


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
            stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                           status_available=bridge.status_available, session_id=bridge.ledger_id)
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
    hud_world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    empty = World.from_script_data(script_data={
        "label": "empty_hud_world", "metadata": {"title": "A quiet world"},
        "scenes": {"quiet": {"blocks": {"start": {"content": "No status provider."}}}},
    })
    register_manual_world(empty)
    try:
        stage = Stage(display_scale=1)
        bridge = PygameSessionBridge()
        first = bridge.start(hud_world.label)
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                       status_available=bridge.status_available, session_id=bridge.ledger_id)
        stage.draw(Turn(step=1))
        original_chrome = stage.chrome
        original_chrome.open = True
        second = bridge.start(empty.label)
        assert first.step == second.step
        assert not bridge.status.sections and bridge.logo_source is None
        assert bridge.branding.name == "A quiet world"
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                       status_available=bridge.status_available, session_id=bridge.ledger_id)
        assert stage.chrome is None and stage.chrome_height == 0
        assert stage.window.get_size() == (320, 200)
        bridge.start(hud_world.label)
        assert "item:lamp" in values(bridge)
        assert bridge.branding.name == "The Workshop"
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                       status_available=bridge.status_available, session_id=bridge.ledger_id)
        assert stage.chrome is not original_chrome and not stage.chrome.open
        assert not stage.chrome.hitboxes
    finally:
        pop_manual_world(empty.label)
        pygame.quit()


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


def test_non_sandbox_custom_provider_uses_the_same_channel_and_scoped_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.presentation.projection import ProjectedState

    world = World.from_script_data(script_data={
        "label": "custom_compact_status", "locals": {"ui_status": [
            {**section("calendar", "24 Brumaire"),
             "hints": {"icon": "alien-calendar", "placement": "end", "icon_only": True}},
            {**section("phase", "Fifth watch"),
             "hints": {"icon": "unknown-phase", "placement": "start"}},
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
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(display_scale=1)
    try:
        bridge = PygameSessionBridge()
        bridge.start(world.label)
        assert values(bridge) == {"calendar": "24 Brumaire", "phase": "Fifth watch"}
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                       status_available=bridge.status_available, session_id=bridge.ledger_id)
        stage.draw(Turn(step=1))
        assert [identity for _box, identity in stage.chrome.hitboxes] == ["phase", "calendar"]
        assert stage.chrome._entry_text(bridge.status.sections[0]) == "calendar: 24 Brumaire"
        height = stage.chrome_height
        pick(bridge, "Next")
        assert not bridge.status.sections
        assert bridge.branding.name == world.label
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                       status_available=bridge.status_available, session_id=bridge.ledger_id)
        stage.draw(Turn(step=1))
        assert stage.chrome_height == height and not stage.chrome.hitboxes
    finally:
        pop_manual_world(world.label)
        pygame.quit()


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
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                       status_available=bridge.status_available, session_id=bridge.ledger_id)
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
        stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                       status_available=bridge.status_available, session_id=bridge.ledger_id)
        stage.draw(frame)
        assert stage.chrome.logo is not None
        assert stage.chrome.height == stage.chrome.line_height + 2 * stage.density
        assert 12 * stage.density <= stage.chrome.height <= 16 * stage.density
        boxes = dict((identity, box) for box, identity in stage.chrome.hitboxes)
        assert set(boxes) == {s.section_id for s in bridge.status.sections}
        assert len({box.top for box in boxes.values()}) == 1
        assert boxes["scene"].right <= boxes["item:bag"].left
        assert boxes["item:lamp"].right <= boxes["day"].left
        assert boxes["day"].right <= boxes["period"].left
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
        stage.set_info(brand, entries, None, status_available=True)
        stage.draw(Turn(step=1))
        boxes = [box for box, _entry in stage.chrome.hitboxes]
        stage.set_info(brand, list(reversed(entries)), None, status_available=True)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boxes[0].center)
        assert stage.chrome.handle_event(click, 1)
        assert stage.chrome.selected_id == "a"
        stage.set_info(brand, [entries[1]], None, status_available=True)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boxes[1].center)
        assert stage.chrome.handle_event(click, 1)
        assert stage.chrome.selected_id == "b"
        stage.set_info(brand, [], None, status_available=True)
        assert stage.chrome.handle_event(click, 1)
        assert not stage.chrome.hitboxes
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
    ], None, status_available=True)
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
    assert stage.chrome.selected_id == "Entry 7" and stage.chrome.page > 0
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN, mod=0)
    stage.chrome.handle_event(event, scale)
    stage.draw(turn)
    assert stage.chrome.detail_page == 1
    stage.chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0), scale)
    assert not stage.chrome.open and stage.hit(screen) == action
    pygame.quit()


@pytest.mark.parametrize("size,scale", [((320, 200), 2), ((640, 400), 1)])
@pytest.mark.parametrize("empty", [[], None])
def test_advertisement_not_content_controls_geometry_and_clears_stale_inspection(
    hud_world: World, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    size: tuple[int, int], scale: int, empty: list | None,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    bridge = PygameSessionBridge()
    envelope = bridge.start(hud_world.label)
    read = Mock(wraps=bridge.service_manager.get_story_info)
    monkeypatch.setattr(bridge.service_manager, "get_story_info", read)
    stage = Stage(logical_size=size, display_scale=scale)
    try:
        def display() -> None:
            stage.set_info(bridge.branding, bridge.status.sections, bridge.logo_source,
                           status_available=bridge.status_available, session_id=bridge.ledger_id)
            stage.draw(Turn(step=1))

        display()
        height = stage.chrome_height
        old = stage.chrome
        old.open = True
        with bridge.service_manager.open_session(user_id=bridge.user_id, write_back=True) as session:
            session.ledger.cursor.locals["ui_status"] = empty
        # A normal dirty-version refresh, not an extra redraw read.
        marker = envelope.metadata["info_state"]
        dirty = envelope.model_copy(update={"metadata": {
            **envelope.metadata, "info_state": {**marker, "version": marker["version"] + 1},
        }})
        bridge._sync(dirty)
        display()
        assert bridge.status_available and not bridge.status.sections
        assert stage.chrome_height == height and not stage.chrome.hitboxes
        assert stage.chrome.selected_id is None
        pygame.image.save(stage.window, str(tmp_path / f"empty-status-{size[0]}.png"))
        # Empty advertised rows still expose branding through their local affordance.
        stage.chrome.open = False
        stage.chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i,
                                                     mod=pygame.KMOD_CTRL), scale)
        stage.draw(Turn(step=1))
        assert stage.chrome.open and stage.chrome.branding.name == "The Workshop"
        removed = dirty.model_copy(update={"metadata": {
            **dirty.metadata, "info_state": {**dirty.metadata["info_state"],
                                             "available_channels": ["ui-sidebar", "time", "inventory"]},
        }})
        bridge._sync(removed)
        display()
        assert stage.chrome is None and stage.chrome_height == 0
        assert stage.window.get_size() == (size[0] * scale, size[1] * scale)
        pygame.image.save(stage.window, str(tmp_path / f"absent-status-{size[0]}.png"))
        assert stage._world_point(stage.window_point((15, 30))) == (15, 30)
        bridge._sync(dirty)
        display()
        assert stage.chrome_height == height and stage.chrome is not old
        assert not stage.chrome.open and not stage.chrome.hitboxes
        assert read.call_count == 2
        for _ in range(3):
            bridge._sync(dirty)
            display()
        assert read.call_count == 2
    finally:
        pygame.quit()


def test_main_branded_world_without_status_has_no_reserved_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.pygame_client import __main__ as client

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    world = World.from_script_data(script_data={
        "label": "branded_without_status", "metadata": {"title": "Only branding"},
        "scenes": {"intro": {"blocks": {"start": {"content": "No status row."}}}},
    })
    register_manual_world(world)
    observed = []

    def events(stage: Stage) -> list[pygame.event.Event]:
        observed.append(stage.window.get_size())
        assert stage.chrome is None and stage.chrome_height == 0
        return [pygame.event.Event(pygame.QUIT)]

    monkeypatch.setattr(client, "_next_events", events)
    try:
        assert client.main(["--world", world.label, "--scale", "1"]) == 0
        assert observed == [(320, 200)]
    finally:
        pop_manual_world(world.label)


def test_entries_sit_on_the_bar_and_only_the_open_one_is_lit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The bar is one opaque ink, and so is every entry on it: a lighter box of
    # its own read as a text wash brightening the bar. Only the entry whose
    # details are open is lit, and a moon's crescent is cut in whatever is
    # behind it.
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(chrome=True, display_scale=1)
    entries = [ProjectedSection(**section("a", "First")),
               ProjectedSection(**section("b", "Night"),
                                hints=PresentationHints(icon="moon", icon_only=True))]
    try:
        stage.set_info(None, entries, None, status_available=True)
        stage.draw(Turn(step=1))
        chrome, d = stage.chrome, stage.chrome.density
        boxes = [box for box, _identity in chrome.hitboxes]
        corner = lambda box: tuple(stage.shell.get_at((box.left + 1, box.bottom - 1)))[:3]
        crescent = (boxes[1].left + 2 * d + 6 * d, (chrome.height - 8 * d) // 2 + 2 * d)
        assert [corner(box) for box in boxes] == [BAR, BAR]
        assert tuple(stage.shell.get_at(crescent))[:3] == BAR

        chrome.selected_id, chrome.open = "b", True
        stage.draw(Turn(step=1))
        assert [corner(box) for box in boxes] == [BAR, SELECTED]
        assert tuple(stage.shell.get_at(crescent))[:3] == SELECTED
    finally:
        pygame.quit()


@pytest.mark.parametrize("size", [(320, 200), (640, 400)])
def test_generic_hints_preserve_group_order_text_floor_and_overflow(
    monkeypatch: pytest.MonkeyPatch, size: tuple[int, int],
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    stage = Stage(logical_size=size, display_scale=1)
    entries = [
        ProjectedSection(**section("z", "End value"), hints=PresentationHints(placement="end")),
        ProjectedSection(**section("b", "Opaque"), hints=PresentationHints(
            placement="middle", icon="key", icon_only=True)),
        ProjectedSection(**section("a", "Beginning"), hints=PresentationHints(placement="start")),
        ProjectedSection(**section("unknown", "Readable"), hints=PresentationHints(
            placement="middle", icon="alien", icon_only=True)),
        ProjectedSection(**section("unhinted", "Default")),
        *[ProjectedSection(**section(str(i), "Long text " * 300)) for i in range(10)],
    ]
    try:
        stage.set_info(None, entries, None, status_available=True)
        chrome = stage.chrome
        pages = chrome._pages()
        flattened = [s.section_id for page in pages for s in page]
        assert flattened == ["a", "unhinted", *map(str, range(10)), "b", "unknown", "z"]
        assert chrome._entry_width(entries[3]) > chrome._entry_width(entries[1])
        assert chrome._entry_text(entries[3]) == "unknown: Readable"
        for _ in entries:
            stage.draw(Turn(step=1))
            boxes = [box for box, _identity in chrome.hitboxes]
            assert all(box.left >= 0 and box.right <= chrome.next_box.left for box in boxes)
            assert all(not first.colliderect(second) for i, first in enumerate(boxes)
                       for second in boxes[i + 1:])
            chrome.open = True
            chrome.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0), 1)
        assert chrome.selected_id == entries[0].section_id
    finally:
        pygame.quit()


@pytest.mark.parametrize("size", [(320, 200), (640, 400)])
def test_authored_icons_render_distinctly_and_graph_json_preserves_hints_and_tokens(
    monkeypatch: pytest.MonkeyPatch, size: tuple[int, int],
) -> None:
    from tangl.mechanics.sandbox.compiler import SandboxSliceCompiler
    from tangl.persistence.serializers import JsonSerializationHandler as Json

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    labels = {"authored_a": "lamp", "authored_b": "key", "authored_c": "bag"}
    compiled = SandboxSliceCompiler().compile({
        "id": "icon_source_witness", "scope": {"id": "scope"},
        "locations": {"room": {"name": "Workshop"}},
        "assets": {label: {"name": "Not the token name", "icon": token,
                           "traits": ["portable"], "initial": {"location": "room"}}
                   for label, token in labels.items()},
    })
    stage = Stage(logical_size=size, display_scale=1)
    try:
        for label in labels:
            compiled.scope.player_assets.add_asset(compiled.locations["room"].remove_asset(label))
        # The ordinary inherited singleton value delegates through the token.
        HudAssetType(label="icon_parent", icon="key")
        inherited = HudAssetType(label="icon_child", inherit_from="icon_parent")
        assert inherited.icon == "key"
        token = EntityTemplate.compile({"kind": Token[HudAssetType], "label": "inherited",
                                        "token_from": "icon_child"}).materialize()
        compiled.graph.add(token)
        compiled.scope.player_assets.add_asset(token)
        room = compiled.locations["room"]
        sections = project_compact_status(
            caller=room, ctx=PhaseCtx(graph=compiled.graph, cursor_id=room.uid),
            request=ProjectionRequest(channels=["ui-status"]),
        )
        expected = {f"item:{label}": icon for label, icon in labels.items()}
        expected["item:inherited"] = "key"
        assert {s.section_id: s.hints.icon for s in sections if s.section_id in expected} == expected
        stage.set_info(None, sections, None, status_available=True)
        stage.draw(Turn(step=1))
        boxes = dict((identity, box) for box, identity in stage.chrome.hitboxes)
        pixels = [pygame.image.tobytes(stage.shell.subsurface(boxes[f"item:{label}"]), "RGB")
                  for label in labels]
        assert len(set(pixels)) == 3
        compiled.scope.locals["ui_status"] = [{
            **section("saved", "Portable hints"),
            "hints": {"placement": "middle", "icon_only": True, "icon": "key"},
        }]
        for graph in (compiled.graph,
                      StoryGraph.structure(compiled.graph.unstructure()),
                      StoryGraph.structure(Json.deserialize(Json.serialize(compiled.graph.unstructure())))):
            scope = graph.find_one(Selector(label="scope"))
            room = graph.find_one(Selector(label="room"))
            override = project_compact_status(caller=room, ctx=PhaseCtx(graph=graph, cursor_id=room.uid),
                                              request=ProjectionRequest(channels=["ui-status"]))
            assert override[0].hints == PresentationHints(icon="key", placement="middle", icon_only=True)
            assert room.parent is scope
            # Holder maps remain the existing excluded staging surface. Verify
            # the persisted graph tokens and their live singleton referents,
            # rather than claiming the holder map is restored by this change.
            for label, icon in {**labels, "inherited": "key"}.items():
                asset = graph.find_one(Selector(label=label))
                assert asset is graph.get(asset.uid) and asset.graph is graph
                assert asset.icon == icon
                assert asset.reference_singleton is (
                    HudAssetType.get_instance("icon_child") if label == "inherited"
                    else SandboxCompiledAssetType.get_instance(label)
                )
    finally:
        pygame.quit()
        HudAssetType.clear_instances()
        for label in labels:
            instance = SandboxCompiledAssetType.get_instance(label)
            if instance is not None:
                SandboxCompiledAssetType._instances.remove(instance.uid)
