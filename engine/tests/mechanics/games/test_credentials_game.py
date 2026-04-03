"""Tests for credential inspection mechanics."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.mechanics.games.handlers import inject_game_context
from tangl.story import Action, Block
from tangl.vm import Ledger, TraversableEdge as ChoiceEdge


class CredentialsBlock(HasGame, Block):
    """Test block embedding credential inspection."""

    _game_class = CredentialsGame
    _game_handler_class = CredentialsGameHandler


class TestCredentialsCore:
    """Core credential game behavior tests."""

    def test_inspect_reveals_hidden_finding(self) -> None:
        game = CredentialsGame()
        handler = CredentialsGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, ("inspect", "passport"))

        assert result.name == "CONTINUE"
        assert "passport" in game.discovered_findings

    def test_correct_disposition_wins(self) -> None:
        game = CredentialsGame(correct_disposition=CredentialDisposition.DENY)
        handler = CredentialsGameHandler()
        handler.setup(game)
        handler.receive_move(game, ("inspect", "passport"))

        result = handler.receive_move(game, ("decide", "deny"))

        assert result.name == "WIN"
        assert game.result.name == "WIN"

    def test_arrest_move_can_be_disabled(self) -> None:
        game = CredentialsGame(allow_arrest=False)
        handler = CredentialsGameHandler()
        handler.setup(game)

        assert ("decide", "arrest") not in handler.get_available_moves(game)

    def test_packet_review_records_packet_finding(self) -> None:
        game = CredentialsGame()
        handler = CredentialsGameHandler()
        handler.setup(game)
        handler.receive_move(game, ("inspect", "passport"))

        result = handler.receive_move(game, ("inspect", "packet consistency"))

        assert result.name == "CONTINUE"
        assert "packet consistency" in game.packet_findings

    def test_blacklist_context_can_force_arrest_disposition(self) -> None:
        game = CredentialsGame(blacklist_status=True)
        handler = CredentialsGameHandler()
        handler.setup(game)
        handler.receive_move(game, ("inspect", "passport"))

        result = handler.receive_move(game, ("decide", "arrest"))

        assert result.name == "WIN"
        assert game.result.name == "WIN"


class TestCredentialsIntegration:
    """VM and HasGame integration tests for credentials."""

    def test_credentials_can_inspect_then_deny_to_victory(self) -> None:
        graph = Graph(label="credential_flow")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = CredentialsBlock.create_game_block(
            graph=graph,
            game_class=CredentialsGame,
            handler_class=CredentialsGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="checkpoint",
        )
        block.game.correct_disposition = CredentialDisposition.DENY
        block.game_handler.setup(block.game)

        intro_to_checkpoint = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Open the checkpoint ledger",
        )

        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_checkpoint.uid)

        inspect = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Inspect passport"
        )
        ledger.resolve_choice(inspect.uid, choice_payload=inspect.payload)

        deny = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Choose deny"
        )
        ledger.resolve_choice(deny.uid, choice_payload=deny.payload)

        assert ledger.cursor_id == victory.uid
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "choose to deny" in content.lower()

    def test_context_exports_discovered_findings(self) -> None:
        graph = Graph(label="credential_context")
        block = graph.add_node(kind=CredentialsBlock, label="checkpoint")
        block.game_handler.setup(block.game)
        block.game_handler.receive_move(block.game, ("inspect", "passport"))

        frame = Ledger.from_graph(graph=graph, entry_id=block.uid).get_frame()
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["credential_num_findings"] == 1
        assert "passport" in namespace["credential_discovered_findings"]
        assert namespace["credential_stage"] == "packet"
