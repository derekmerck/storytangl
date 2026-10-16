"""Service JSON reopen witnesses for game state, not selected action payloads.

The fixture plays one typed round directly through the rule handler inside a
writeback session. After reopen, consumers use history before any next selected
move reaches UPDATE. Service play/restore/play belongs to #551 Pass 2.
"""

from __future__ import annotations

import json

import pytest

from tangl.mechanics.games import HasGame, NimGame, NimGameHandler, NimMove
from tangl.mechanics.games.enums import GamePhase, RoundResult
from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler, RpsMove
from tangl.mechanics.games.strategies import opponent_strategies
from tangl.persistence import PersistenceManagerFactory
from tangl.presentation.intent import QuantityAccepts
from tangl.service.service_manager import ServiceManager
from tangl.service.user.user import User
from tangl.story import Block, InitMode, World


class RpsStateWitnessBlock(HasGame, Block):
    _game_class = RpsGame
    _game_handler_class = RpsGameHandler


class NimStateWitnessBlock(HasGame, Block):
    _game_class = NimGame
    _game_handler_class = NimGameHandler


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
