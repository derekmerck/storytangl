"""JSON-backed selected-action play/reopen/play and pre-UPDATE history consumers.

The original Pass 1 seeded-state witness remains alongside real selected-action
play, so typed restoration is also checked independently of another UPDATE.
"""

from __future__ import annotations

import json
import random

import pytest

from tangl.mechanics.games import HasGame, NimGame, NimGameHandler, NimMove
from tangl.mechanics.games.enums import GamePhase, RoundResult
from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler, RpsMove
from tangl.mechanics.games.strategies import opponent_strategies
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.presentation.intent import QuantityAccepts
from tangl.service.service_manager import ServiceManager
from tangl.service.response import DirectEdgeRequest
from tangl.service.user.user import User
from tangl.story import Action, Block, InitMode, World


class RpsStateWitnessBlock(HasGame, Block):
    _game_class = RpsGame
    _game_handler_class = RpsGameHandler


class NimStateWitnessBlock(HasGame, Block):
    _game_class = NimGame
    _game_handler_class = NimGameHandler


class JsonRpsMatch(RpsGame):
    scoring_n: int = 10
    opponent_strategy: str = "rps_rock"


class JsonRpsMatchBlock(RpsStateWitnessBlock):
    _game_class = JsonRpsMatch


class JsonNimMatch(NimGame):
    opening_heaps: dict[str, int] = {"red": 20, "blue": 20}
    opponent_strategy: str = "nim_greedy"


class JsonNimMatchBlock(NimStateWitnessBlock):
    _game_class = JsonNimMatch


def _json_match(block_class):
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="json_sqlite_in_mem",
    )
    manager = ServiceManager(persistence)
    user = User(label="selected_moves")
    persistence.save(user)
    world = World.from_script_data(script_data={
        "label": "selected_move_match",
        "metadata": {"title": "Match", "author": "Tests", "start_at": "table.game"},
        "scenes": {"table": {"blocks": {"game": {"kind": block_class}}}},
    })
    manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    return persistence, manager, user


@pytest.mark.parametrize("block_class", [JsonRpsMatchBlock, JsonNimMatchBlock])
@pytest.mark.parametrize("echo_move", [False, True])
def test_service_selected_moves_play_restore_and_play_with_json_wire_input(
    block_class, echo_move: bool,
) -> None:
    persistence, manager, user = _json_match(block_class)

    for round_index in range(2):
        # A new manager and open session load flat JSON, not the prior live graph.
        manager = ServiceManager(persistence)
        with manager.open_session(user_id=user.uid) as session:
            game = session.ledger.cursor.game_state
            assert game.round == round_index
            if round_index:
                assert type(game.history[0].player_move) is (RpsMove if isinstance(game, RpsGame) else NimMove)
                assert type(game.history[0].opponent_move) is type(game.history[0].player_move)
                assert type(game.opponent_next_move) is type(game.history[0].player_move)
                namespace = session.frame._make_ctx().get_ns(session.ledger.cursor)
                assert namespace["last_player_move"] == game.history[0].player_move
                if isinstance(game, RpsGame):
                    assert opponent_strategies.execute("rps_tit_for_tat", game) is RpsMove.PAPER
                    assert "You played paper." in [
                        fragment.content for fragment in session.ledger.cursor.game_handler.get_journal_fragments(game)
                    ]
            moves = [edge for edge in session.ledger.cursor.edges_out() if isinstance(edge, Action)]
            if isinstance(game, RpsGame):
                edge = next(edge for edge in moves if edge.payload["move"] == "paper")
                assert isinstance(edge.payload["move"], str)
                submitted = {"move": "paper"} if echo_move else None
            else:
                edge = next(edge for edge in moves if edge.payload["move"]["pile"] == "red")
                assert isinstance(edge.payload["move"], dict)
                assert edge.payload["move"]["count"] == 0
                assert edge.accepts.kind == "quantity"
                submitted = {"quantity": round_index + 1}
                if echo_move:
                    submitted["move"] = edge.payload["move"]
            edge_id = edge.uid
            ledger_id = session.ledger.uid

        wire = Json.deserialize(Json.serialize(submitted))
        manager.resolve_choice(
            user_id=user.uid, request=DirectEdgeRequest(edge_id=edge_id, payload=wire),
        )
        assert isinstance(persistence.storage[ledger_id], str)

    with ServiceManager(persistence).open_session(user_id=user.uid) as session:
        game = session.ledger.cursor.game_state
        assert len(game.history) == 2
        if isinstance(game, RpsGame):
            assert game.history[-1].player_move is RpsMove.PAPER
        else:
            assert game.history[-1].player_move == NimMove("red", 2)


@pytest.mark.parametrize("block_class", [JsonRpsMatchBlock, JsonNimMatchBlock])
def test_service_and_live_reopened_ledger_reject_otherwise_legal_substitution(block_class) -> None:
    persistence, manager, user = _json_match(block_class)
    with manager.open_session(user_id=user.uid) as session:
        host = session.ledger.cursor
        actions = [edge for edge in host.edges_out() if isinstance(edge, Action)]
        if isinstance(host.game_state, RpsGame):
            edge = next(edge for edge in actions if edge.payload["move"] == "paper")
            payload = {"move": "rock"}
        else:
            edge = next(edge for edge in actions if edge.payload["move"]["pile"] == "red")
            payload = {"move": {"pile": "blue", "count": 0}, "quantity": 1}
        payload = json.loads(Json.serialize(payload))
        before = Json.serialize(session.ledger.unstructure()), random.getstate()
        with pytest.raises(ValueError, match="Cannot replace offered game binding"):
            session.ledger.resolve_choice(edge.uid, choice_payload=payload)
        assert (Json.serialize(session.ledger.unstructure()), random.getstate()) == before
        ledger_id = session.ledger.uid
    stored_before = persistence.storage[ledger_id]
    with pytest.raises(ValueError, match="Cannot replace offered game binding"):
        manager.resolve_choice(
            user_id=user.uid, request=DirectEdgeRequest(edge_id=edge.uid, payload=payload),
        )
    assert persistence.storage[ledger_id] == stored_before


@pytest.mark.parametrize("block_class", [RpsStateWitnessBlock, NimStateWitnessBlock])
def test_json_service_session_restores_history_before_another_selected_move(
    block_class: type[RpsStateWitnessBlock | NimStateWitnessBlock],
) -> None:
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="json_sqlite_in_mem",
    )
    manager = ServiceManager(persistence)
    user = User(label="game_state_reader")
    persistence.save(user)
    world = World.from_script_data(script_data={
        "label": "game_state_reopen",
        "metadata": {"title": "State reopen", "author": "Tests", "start_at": "table.game"},
        "scenes": {"table": {"blocks": {"game": {"kind": block_class}}}},
    })
    manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER,
    )

    with manager.open_session(user_id=user.uid, write_back=True) as session:
        host = session.ledger.cursor
        assert isinstance(host, block_class)
        game = host.game
        if isinstance(game, RpsGame):
            player, opponent = RpsMove.PAPER, RpsMove.ROCK
            game.opponent_strategy = "rps_rock"
        else:
            assert isinstance(game, NimGame)
            player, opponent = NimMove("heap", 1), NimMove("heap", 1)
            game.opponent_strategy = "nim_greedy"
        game.opponent_next_move = opponent
        host.game_handler.receive_move(game, player)
        expected_pending = game.opponent_next_move
        assert expected_pending is not None
        assert game.phase is GamePhase.READY
        ledger_id = session.ledger.uid

    stored = persistence.storage[ledger_id]
    assert isinstance(stored, str)
    assert json.loads(stored)["kind"] == "Ledger"
    reopened_manager = ServiceManager(persistence)
    with reopened_manager.open_session(user_id=user.uid, write_back=False) as session:
        restored_host = session.ledger.cursor
        assert isinstance(restored_host, block_class)
        restored = restored_host.game_state
        assert restored is not game
        assert type(restored) is type(game)
        assert type(restored.history[0].player_move) is type(player)
        assert type(restored.history[0].opponent_move) is type(opponent)
        assert type(restored.opponent_next_move) is type(expected_pending)
        assert restored.history[0].player_move == player
        assert restored.history[0].opponent_move == opponent
        assert restored.opponent_next_move == expected_pending
        assert restored.history[0].result in (RoundResult.WIN, RoundResult.CONTINUE)

        # The normal phase namespace reads history and the pending tell without UPDATE.
        namespace = session.frame._make_ctx().get_ns(restored_host)
        assert namespace["last_player_move"] == player
        assert namespace["last_opponent_move"] == opponent
        assert namespace["opponent_next_move"] == expected_pending
        if isinstance(restored, RpsGame):
            assert opponent_strategies.execute("rps_tit_for_tat", restored) is RpsMove.PAPER
            text = [
                fragment.content
                for fragment in restored_host.game_handler.get_journal_fragments(restored)
            ]
            assert "You played paper." in text
            assert "Opponent played rock." in text
            assert "Paper covers rock You won this round!" in text
            assert "*Your opponent is preparing rock...*" in text
        else:
            assert namespace["last_player_move"].pile == "heap"
            assert namespace["last_opponent_move"].count == 1
            assert namespace["opponent_next_move"].count == 3
            assert restored.heaps["heap"] == 5
            selector = restored_host.game_handler.get_provisioned_moves(restored)[0]
            assert selector == NimMove("heap", 0)
            assert isinstance(
                restored_host.game_handler.get_move_accepts(restored, selector), QuantityAccepts,
            )
