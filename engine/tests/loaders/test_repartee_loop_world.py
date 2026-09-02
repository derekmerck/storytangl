"""Integration coverage for the launchable repartee reference world."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment, MediaFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.games import CallResponseExchange, GameResult
from tangl.service.dispatch import do_advertise_info_channels, do_get_story_info
from tangl.service.response import StoryInfoRequest
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger
from tangl.vm.runtime.frame import PhaseCtx


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _repartee_root() -> Path:
    return _repo_worlds_dir() / "repartee_loop"


def _action(ledger: Ledger, text: str) -> Action:
    """Find one stable or projected action by its authored display text."""

    action = next(
        edge
        for edge in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if edge.text == text
    )
    assert isinstance(action, Action)
    return action


def _choices(ledger: Ledger) -> list[ChoiceFragment]:
    """Return the choice fragments projected for the current step."""

    return [
        fragment
        for fragment in ledger.get_journal()
        if isinstance(fragment, ChoiceFragment) and fragment.step == ledger.step
    ]


def _choice(ledger: Ledger, text: str) -> ChoiceFragment:
    """Return the current journal projection for one authored choice."""

    choice = next(
        fragment
        for fragment in reversed(ledger.get_journal())
        if isinstance(fragment, ChoiceFragment) and fragment.text == text
    )
    return choice


class TestReparteeLoopWorld:
    """Loader and ordinary Ledger proof for the compact reference world."""

    def test_world_registry_discovers_repartee_loop(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "repartee_loop" in registry.bundles
        bundle = registry.bundles["repartee_loop"]
        assert bundle.manifest.label == "repartee_loop"
        assert bundle.manifest.metadata["title"] == "Repartee Loop"

    def test_repartee_loop_awards_reply_then_prize_and_reaches_salon(self) -> None:
        bundle = WorldBundle.load(_repartee_root())
        world = WorldCompiler().compile(bundle)
        from repartee_loop.domain import (
            DockhandContestBlock,
            MasterContestBlock,
            ReparteeParticipant,
        )

        assert "DockhandContestBlock" in world.class_registry
        assert "MasterContestBlock" in world.class_registry
        result = world.create_story("repartee_loop_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"
        ledger.resolve_choice(_action(ledger, "Step into the practice court").uid)
        assert ledger.cursor.label == "setup"
        ledger.resolve_choice(_action(ledger, "Step out onto the quay").uid)

        assert ledger.cursor.label == "quay_map"
        assert _choice(ledger, "Go to The Practice Yard").available is True
        assert _choice(ledger, "Go to The Salon Terrace").available is False
        assert _choice(ledger, "Go to The Salon").available is False

        ledger.resolve_choice(_action(ledger, "Go to The Practice Yard").uid)
        assert ledger.cursor.label == "practice_yard"
        ledger.resolve_choice(_action(ledger, "Challenge the dockhand").uid)
        assert ledger.cursor.label == "dockhand_contest"
        dockhand = ledger.cursor
        assert isinstance(dockhand, DockhandContestBlock)
        starter_action = next(
            edge
            for edge in dockhand.edges_out(Selector(has_kind=Action, trigger_phase=None))
            if edge.payload == {"move": "repartee_starter_call"}
        )
        ledger.resolve_choice(starter_action.uid, choice_payload=starter_action.payload)

        assert ledger.cursor.label == "dockhand_aftermath"
        dockhand_round = dockhand.game.last_round
        assert dockhand_round is not None
        dockhand_exchange = CallResponseExchange.model_validate(dockhand_round.notes)
        assert dockhand_exchange.response_phrase_id == "repartee_reply"
        assert dockhand.game.result is GameResult.LOSE
        player = result.graph.find_one(Selector(label="player"))
        assert isinstance(player, ReparteeParticipant)
        assert player.repertoire.phrase_ids() == ["repartee_reply", "repartee_starter_call"]
        assert ledger.cursor.locals["awarded_phrase_ids"] == ["repartee_reply"]

        ledger.resolve_choice(_action(ledger, "Step back into the yard").uid)
        assert ledger.cursor.label == "practice_yard"
        assert _choice(ledger, "Challenge the dockhand").available is False
        ledger.resolve_choice(_action(ledger, "Return to the map").uid)

        assert ledger.cursor.label == "quay_map"
        assert _choice(ledger, "Go to The Salon Terrace").available is True
        assert _choice(ledger, "Go to The Salon").available is False

        ledger.resolve_choice(_action(ledger, "Go to The Salon Terrace").uid)
        assert ledger.cursor.label == "salon_terrace"
        ledger.resolve_choice(_action(ledger, "Challenge the salon master").uid)
        assert ledger.cursor.label == "master_contest"
        master = ledger.cursor
        assert isinstance(master, MasterContestBlock)
        assert master.game.player_phrase_ids == ["repartee_reply", "repartee_starter_call"]
        assert master.game.opponent_phrase_ids == ["repartee_master_call"]
        assert player.repertoire.has_phrase("repartee_master_call") is False
        assert [
            (
                match.call_phrase_id,
                match.response_phrase_id,
                match.matched,
                match.source_id,
            )
            for match in master.game.schedule
        ] == [
            (
                "repartee_master_call",
                "repartee_reply",
                True,
                "repartee-master-catalog",
            ),
        ]
        reply_action = next(
            edge
            for edge in master.edges_out(Selector(has_kind=Action, trigger_phase=None))
            if edge.payload == {"move": "repartee_reply"}
        )
        ledger.resolve_choice(reply_action.uid, choice_payload=reply_action.payload)

        assert ledger.cursor.label == "prize_aftermath"
        master_round = master.game.last_round
        assert master_round is not None
        master_exchange = CallResponseExchange.model_validate(master_round.notes)
        assert master_exchange.call_phrase_id == "repartee_master_call"
        assert master_exchange.response_phrase_id == "repartee_reply"
        assert master_exchange.matched is True
        assert master.game.result is GameResult.WIN
        assert player.repertoire.phrase_ids() == ["repartee_reply", "repartee_starter_call"]
        assert player.prizes.prize_ids() == ["repartee_salon_token"]
        prize = player.prizes.get_slot("known_prizes")[0]
        assert result.graph.get(prize.uid) is prize
        assert ledger.cursor.locals["awarded_prize_ids"] == ["repartee_salon_token"]

        ledger.resolve_choice(_action(ledger, "Step back onto the terrace").uid)
        assert ledger.cursor.label == "salon_terrace"
        assert _choice(ledger, "Challenge the salon master").available is False
        ledger.resolve_choice(_action(ledger, "Return to the map").uid)

        assert ledger.cursor.label == "quay_map"
        assert _choice(ledger, "Go to The Salon").available is True
        ledger.resolve_choice(_action(ledger, "Go to The Salon").uid)

        assert ledger.cursor.label == "salon"
        journal_text = [
            fragment.content
            for fragment in ledger.get_journal()
            if isinstance(fragment, ContentFragment)
        ]
        assert any("Your argument arrives" in text for text in journal_text)
        assert any("Then it has walked" in text for text in journal_text)
        assert any("You win the exchange" in text for text in journal_text)

    def test_repartee_map_hub_offers_every_region_the_district_claims(self) -> None:
        """The plate's four regions each have a live choice behind them."""

        bundle = WorldBundle.load(_repartee_root())
        world = WorldCompiler().compile(bundle)
        result = world.create_story("repartee_map_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        ledger.resolve_choice(_action(ledger, "Step into the practice court").uid)
        ledger.resolve_choice(_action(ledger, "Step out onto the quay").uid)

        travel = {
            choice.text: choice
            for choice in _choices(ledger)
            if choice.tags
        }
        assert {choice.text for choice in travel.values()} == {
            "Go to The Quayside",
            "Go to The Practice Yard",
            "Go to The Salon Terrace",
            "Go to The Salon",
        }
        assert {tag for choice in travel.values() for tag in choice.tags} == {
            "ui:plate:quay:quayside",
            "ui:plate:quay:practice_yard",
            "ui:plate:quay:salon_terrace",
            "ui:plate:quay:salon",
        }

    def test_repartee_map_dims_the_salon_rather_than_hiding_it(self) -> None:
        """A guarded place stays on the plate, tagged, with a reason."""

        bundle = WorldBundle.load(_repartee_root())
        world = WorldCompiler().compile(bundle)
        result = world.create_story("repartee_dim_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        ledger.resolve_choice(_action(ledger, "Step into the practice court").uid)
        ledger.resolve_choice(_action(ledger, "Step out onto the quay").uid)

        salon = _choice(ledger, "Go to The Salon")
        assert salon.available is False
        assert salon.unavailable_reason
        assert salon.tags == {"ui:plate:quay:salon"}

    def test_repartee_publishes_plate_geometry_on_its_own_channel(self) -> None:
        """Geometry is served, and the reader-facing map channel stays prose."""

        bundle = WorldBundle.load(_repartee_root())
        world = WorldCompiler().compile(bundle)
        result = world.create_story("repartee_plate_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        ledger.resolve_choice(_action(ledger, "Step into the practice court").uid)
        ledger.resolve_choice(_action(ledger, "Step out onto the quay").uid)

        ctx = PhaseCtx(
            graph=result.graph,
            cursor_id=ledger.cursor.uid,
            step=ledger.step,
        )
        advertised = {a.kind for a in do_advertise_info_channels(ledger.cursor, ctx=ctx)}
        assert {"map", "map_plate"} <= advertised

        state = do_get_story_info(
            ledger.cursor,
            ctx=ctx,
            request=StoryInfoRequest(kinds=["map_plate", "map_regions"]),
        )
        sections = {section.section_id: section for section in state.sections}
        regions = sections["sandbox_map_regions"]
        assert regions.value.columns == ["Region", "x", "y", "w", "h"]
        assert [row[0] for row in regions.value.rows] == [
            "practice_yard",
            "quayside",
            "salon",
            "salon_terrace",
        ]

        gazetteer = do_get_story_info(
            ledger.cursor,
            ctx=ctx,
            request=StoryInfoRequest(kind="map"),
        )
        assert not any(
            section.section_id.startswith("sandbox_map_region")
            for section in gazetteer.sections
        )

    def test_repartee_plate_rides_as_media_the_stage_will_not_mistake_for_scenery(
        self,
    ) -> None:
        """The plate is media with an info role, so no client stages it as a
        background. A client that draws maps looks for it by role."""

        bundle = WorldBundle.load(_repartee_root())
        world = WorldCompiler().compile(bundle)
        result = world.create_story("repartee_plate_media", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        ledger.resolve_choice(_action(ledger, "Step into the practice court").uid)
        ledger.resolve_choice(_action(ledger, "Step out onto the quay").uid)

        roles = {
            fragment.media_role
            for fragment in ledger.get_journal()
            if isinstance(fragment, MediaFragment) and fragment.step == ledger.step
        }
        assert "map_im" in roles
        assert "narrative_im" not in roles
