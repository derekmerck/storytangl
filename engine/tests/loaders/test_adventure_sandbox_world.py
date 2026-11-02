"""Tests for the Adventure-style sandbox demo world bundle."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector, Token
from tangl.journal.fragments import ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.sandbox import SandboxCompiledAssetType, SandboxLocation
from tangl.presentation.projection import KvListValue, ProjectionRequest
from tangl.service.dispatch import do_get_story_info
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _adventure_root() -> Path:
    return _repo_worlds_dir() / "adventure_sandbox_slice"


def _provision_sandbox_actions(ledger: Ledger) -> list[Action]:
    assert isinstance(ledger.cursor, SandboxLocation)
    do_provision(
        ledger.cursor,
        ctx=PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor.uid),
    )
    return [
        edge
        for edge in ledger.cursor.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox"}.issubset(edge.tags)
    ]


def _choose(ledger: Ledger, **hints: str) -> Action:
    for action in _provision_sandbox_actions(ledger):
        action_hints = action.ui_hints.model_dump()
        if all(action_hints.get(key) == value for key, value in hints.items()):
            ledger.resolve_choice(action.uid, choice_payload=action.payload)
            return action
    raise AssertionError(f"No sandbox action at {ledger.cursor.label!r} matched {hints!r}")


class TestAdventureSandboxWorld:
    """Tests for the real Adventure-style sandbox demo world."""

    def test_world_registry_discovers_adventure_sandbox_slice(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "adventure_sandbox_slice" in registry.bundles
        bundle = registry.bundles["adventure_sandbox_slice"]
        assert bundle.manifest.label == "adventure_sandbox_slice"
        assert bundle.manifest.metadata["title"] == "Grand Grotto"

    def test_shared_grate_is_local_to_each_story(self) -> None:
        world = WorldCompiler().compile(WorldBundle.load(_adventure_root()))
        ledgers = []
        for label in ("first", "second"):
            graph = world.create_story(label).graph
            ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
            enter = next(edge for edge in ledger.cursor.edges_out() if isinstance(edge, Action))
            ledger.resolve_choice(enter.uid)
            ledgers.append(ledger)
        fixtures = []
        for ledger in ledgers:
            outside = ledger.graph.find_one(Selector(label="outside_grate"))
            below = ledger.graph.find_one(Selector(label="below_grate"))
            fixture = outside.fixture_by_label("grate")
            assert fixture is below.fixture_by_label("grate")
            fixtures.append(fixture)
        assert fixtures[0].uid != fixtures[1].uid
        fixtures[0].lockable.is_locked = False
        fixtures[0].openable.is_open = True
        assert fixtures[1].locked and not fixtures[1].open

    def test_frozen_sandbox_prepares_wallets_during_story_setup(self) -> None:
        world = WorldCompiler().compile(WorldBundle.load(_adventure_root()))
        graph = world.create_story("frozen", freeze_shape=True).graph
        scope = graph.find_one(Selector(label="cave"))
        building = graph.find_one(Selector(label="building"))
        assert scope.player_assets.discrete_wallet_id is not None
        assert building.discrete_wallet_id is not None
        before = graph.value_hash(), len(graph.members)
        assert building.get_asset("brass_lamp") is not None
        assert not scope.player_assets.assets
        assert (graph.value_hash(), len(graph.members)) == before

    def test_catalog_is_world_owned_and_story_token_state_is_isolated(self) -> None:
        world = WorldCompiler().compile(WorldBundle.load(_adventure_root()))
        catalog = next(c for c in world.get_token_catalogs() if c.label == "adventure")
        definition = next(catalog.find_all(Selector(catalog_id="brass_lamp")))
        assert definition.label == "adventure_sandbox_slice:adventure:brass_lamp"
        assert definition.charge.current == 330

        ledgers = [
            Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
            for result in (world.create_story("first"), world.create_story("second"))
        ]
        for ledger in ledgers:
            enter = next(a for a in ledger.cursor.edges_out() if isinstance(a, Action))
            ledger.resolve_choice(enter.uid)
        lamps = [ledger.graph.find_one(Selector(label="brass_lamp")) for ledger in ledgers]
        assert all(isinstance(lamp, Token[SandboxCompiledAssetType]) for lamp in lamps)
        assert lamps[0].uid != lamps[1].uid
        assert lamps[0].reference_singleton is lamps[1].reference_singleton is definition
        lamps[0].lit = True
        lamps[0].charge.current = 12
        assert not lamps[1].lit and lamps[1].charge.current == 330
        assert definition.charge.current == 330

    def test_adventure_sandbox_world_runs_core_walkthrough(self) -> None:
        bundle = WorldBundle.load(_adventure_root())
        world = WorldCompiler().compile(bundle)

        assert "AdventureSandboxLocation" in world.class_registry

        result = world.create_story("adventure_sandbox_slice", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        enter = next(
            edge
            for edge in ledger.cursor.edges_out()
            if isinstance(edge, Action)
            and edge.text == "Stand at the end of the road"
        )
        ledger.resolve_choice(enter.uid)

        assert ledger.cursor.label == "road"

        _choose(ledger, contribution="movement", direction="east")
        _choose(ledger, contribution="take", asset="keys")
        _choose(ledger, contribution="take", asset="brass_lamp")
        _choose(ledger, contribution="light", asset="brass_lamp", verb="turn_on")
        _choose(ledger, contribution="movement", direction="west")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="unlock", target="grate")
        _choose(ledger, contribution="open", target="grate")
        _choose(ledger, contribution="movement", direction="down")
        _choose(ledger, contribution="movement", direction="west")

        assert ledger.cursor.label == "cobble_crawl"

        _choose(ledger, contribution="take", asset="gold_nugget")
        _choose(ledger, contribution="mob", mob="wounded_pirate", action="help")
        _choose(ledger, contribution="magic_word", word="XYZZY")

        assert ledger.cursor.label == "building"

        _choose(ledger, contribution="deposit_treasure", asset="gold_nugget")

        projected = do_get_story_info(
            ledger.cursor,
            ctx=PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor.uid),
            request=ProjectionRequest(channels=["ui-score"]),
        )
        score_section = next(
            section
            for section in projected.sections
            if section.section_id == "adventure_score"
        )
        assert isinstance(score_section.value, KvListValue)
        assert [(row.key, row.value) for row in score_section.value.items] == [
            ("Score", 10),
            ("Deposited", 1),
        ]

        content = [
            fragment.content
            for fragment in ledger.get_journal()
            if isinstance(fragment, ContentFragment)
        ]
        assert "The key turns with a click. The grate unlocks." in content
        assert "A wounded pirate leans against the wall, watching you." in content
        assert "The pirate eyes you suspiciously, but accepts your help." in content
        assert "A hollow voice says \"Plugh.\" You are back in the well house." in content
        assert (
            "The gold nugget is safely deposited in the well house. "
            "Your score has increased."
        ) in content

    def test_adventure_movement_hazard_blocks_heavy_nugget_climb(self) -> None:
        bundle = WorldBundle.load(_adventure_root())
        world = WorldCompiler().compile(bundle)
        result = world.create_story("adventure_sandbox_slice", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        enter = next(
            edge
            for edge in ledger.cursor.edges_out()
            if isinstance(edge, Action)
            and edge.text == "Stand at the end of the road"
        )
        ledger.resolve_choice(enter.uid)

        _choose(ledger, contribution="movement", direction="east")
        _choose(ledger, contribution="take", asset="keys")
        _choose(ledger, contribution="take", asset="brass_lamp")
        _choose(ledger, contribution="light", asset="brass_lamp", verb="turn_on")
        _choose(ledger, contribution="movement", direction="west")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="movement", direction="south")
        _choose(ledger, contribution="unlock", target="grate")
        _choose(ledger, contribution="open", target="grate")
        _choose(ledger, contribution="movement", direction="down")
        _choose(ledger, contribution="movement", direction="west")
        _choose(ledger, contribution="take", asset="gold_nugget")
        _choose(ledger, contribution="movement", direction="west")

        assert ledger.cursor.label == "hall_of_mists"

        _choose(ledger, contribution="movement_hazard", direction="up")

        assert ledger.cursor.label == "hall_of_mists"

        _choose(ledger, contribution="drop", asset="gold_nugget")
        _choose(ledger, contribution="movement", direction="up")

        assert ledger.cursor.label == "top_of_small_pit"

        content = [
            fragment.content
            for fragment in ledger.get_journal()
            if isinstance(fragment, ContentFragment)
        ]
        assert (
            "I'm not sure you'll be able to get up it with what you're carrying."
            in content
        )
