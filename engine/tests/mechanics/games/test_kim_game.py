"""Tests for Kim's Game style picking mechanics."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.kim_game import KimGame, KimGameHandler
from tangl.mechanics.games.handlers import inject_game_context
from tangl.story import Action, Block
from tangl.vm import Ledger, TraversableEdge as ChoiceEdge


class KimBlock(HasGame, Block):
    """Test block embedding a Kim's Game contest."""

    _game_class = KimGame
    _game_handler_class = KimGameHandler


class TestKimCore:
    """Core Kim's Game behavior tests."""

    def test_setup_selects_missing_item_when_needed(self) -> None:
        game = KimGame(selection_seed=7)
        handler = KimGameHandler()

        handler.setup(game)

        assert game.missing_item in game.tray_items
        assert game.remaining_cues == game.cue_budget

    def test_inspect_move_reveals_cue(self) -> None:
        game = KimGame(missing_item="silver thimble")
        handler = KimGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, ("inspect", "material"))

        assert result.name == "CONTINUE"
        assert game.remaining_cues == 1
        assert "metallic" in game.revealed_cues[0]

    def test_correct_guess_wins(self) -> None:
        game = KimGame(missing_item="silver thimble")
        handler = KimGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, ("guess", "silver thimble"))

        assert result.name == "WIN"
        assert game.result.name == "WIN"

    def test_wrong_guess_loses(self) -> None:
        game = KimGame(missing_item="silver thimble")
        handler = KimGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, ("guess", "ivory die"))

        assert result.name == "LOSE"
        assert game.result.name == "LOSE"


class TestKimIntegration:
    """VM and HasGame integration tests for Kim's Game."""

    def test_kim_game_can_inspect_then_guess_to_victory(self) -> None:
        graph = Graph(label="kim_flow")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = KimBlock.create_game_block(
            graph=graph,
            game_class=KimGame,
            handler_class=KimGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="tray",
        )
        block.game.missing_item = "silver thimble"
        block.game_handler.setup(block.game)

        intro_to_tray = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Study the tray",
        )

        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_tray.uid)

        inspect = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Inspect the material cue"
        )
        ledger.resolve_choice(inspect.uid, choice_payload=inspect.payload)

        assert ledger.cursor.label == "tray"

        guess = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Guess silver thimble"
        )
        ledger.resolve_choice(guess.uid, choice_payload=guess.payload)

        assert ledger.cursor_id == victory.uid
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "name the missing object correctly" in content.lower()

    def test_context_exports_revealed_cues(self) -> None:
        graph = Graph(label="kim_context")
        block = graph.add_node(kind=KimBlock, label="tray")
        block.game.missing_item = "silver thimble"
        block.game_handler.setup(block.game)
        block.game_handler.receive_move(block.game, ("inspect", "material"))

        frame = ledger_frame = Ledger.from_graph(graph=graph, entry_id=block.uid).get_frame()
        ctx = ledger_frame._make_ctx()
        object.__setattr__(ctx, "_frame", ledger_frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["kim_remaining_cues"] == 1
        assert namespace["kim_revealed_cues"]
