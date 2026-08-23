"""Integration coverage for the launchable repartee reference world."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.games import CallResponseExchange, GameResult
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger


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

        assert "DockhandContestBlock" in world.class_registry
        assert "MasterContestBlock" in world.class_registry
        result = world.create_story("repartee_loop_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"
        ledger.resolve_choice(_action(ledger, "Step into the practice court").uid)
        assert ledger.cursor.label == "setup"
        ledger.resolve_choice(_action(ledger, "Enter the quay hub").uid)

        assert ledger.cursor.label == "hub"
        assert _choice(ledger, "Challenge the dockhand").available is True
        assert _choice(ledger, "Challenge the salon master").available is False
        assert _choice(ledger, "Enter the salon").available is False

        ledger.resolve_choice(_action(ledger, "Challenge the dockhand").uid)
        assert ledger.cursor.label == "dockhand_contest"
        dockhand = ledger.cursor
        starter_action = next(
            edge
            for edge in dockhand.edges_out(Selector(has_kind=Action, trigger_phase=None))
            if edge.payload == {"move": "repartee_starter_call"}
        )
        ledger.resolve_choice(starter_action.uid, choice_payload=starter_action.payload)

        assert ledger.cursor.label == "dockhand_aftermath"
        dockhand_exchange = CallResponseExchange.model_validate(dockhand.game.last_round.notes)
        assert dockhand_exchange.response_phrase_id == "repartee_reply"
        assert dockhand.game.result is GameResult.LOSE
        player = result.graph.find_one(Selector(label="player"))
        assert player is not None
        assert player.repertoire.phrase_ids() == ["repartee_reply", "repartee_starter_call"]
        assert ledger.cursor.locals["awarded_phrase_ids"] == ["repartee_reply"]

        ledger.resolve_choice(_action(ledger, "Return to the quay hub").uid)
        assert ledger.cursor.label == "hub"
        assert _choice(ledger, "Challenge the dockhand").available is False
        assert _choice(ledger, "Challenge the salon master").available is True
        assert _choice(ledger, "Enter the salon").available is False

        ledger.resolve_choice(_action(ledger, "Challenge the salon master").uid)
        assert ledger.cursor.label == "master_contest"
        master = ledger.cursor
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
        master_exchange = CallResponseExchange.model_validate(master.game.last_round.notes)
        assert master_exchange.call_phrase_id == "repartee_master_call"
        assert master_exchange.response_phrase_id == "repartee_reply"
        assert master_exchange.matched is True
        assert master.game.result is GameResult.WIN
        assert player.repertoire.phrase_ids() == ["repartee_reply", "repartee_starter_call"]
        assert player.prizes.prize_ids() == ["repartee_salon_token"]
        prize = player.prizes.get_slot("known_prizes")[0]
        assert result.graph.get(prize.uid) is prize
        assert ledger.cursor.locals["awarded_prize_ids"] == ["repartee_salon_token"]

        ledger.resolve_choice(_action(ledger, "Return to the quay hub").uid)
        assert ledger.cursor.label == "hub"
        assert _choice(ledger, "Enter the salon").available is True
        ledger.resolve_choice(_action(ledger, "Enter the salon").uid)

        assert ledger.cursor.label == "salon"
        journal_text = [
            fragment.content
            for fragment in ledger.get_journal()
            if isinstance(fragment, ContentFragment)
        ]
        assert any("Your argument arrives" in text for text in journal_text)
        assert any("Then it has walked" in text for text in journal_text)
        assert any("You win the exchange" in text for text in journal_text)
