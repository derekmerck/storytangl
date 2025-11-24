"""
Tests for the game core state machine.

These tests verify the pure domain logic without any VM dependencies.
"""
import pytest
from tangl.mechanics.games import (
    GamePhase,
    GameResult,
    RoundResult,
    Game,
    GameHandler,
    opponent_strategies,
    scoring_strategies,
)
from tangl.mechanics.games.trivial_game import (
    TrivialMove,
    TrivialGame,
    TrivialGameHandler,
)
from tangl.mechanics.games.rps_game import (
    RpsMove,
    RpsGame,
    RpsGameHandler,
    RpslsMove,
    RpslsGame,
    RpslsGameHandler,
)

class TestGameLifecycle:
    """Test the game phase state machine."""
    
    def test_game_starts_pending(self):
        game = TrivialGame()
        assert game.phase == GamePhase.PENDING
        assert game.result == GameResult.IN_PROCESS
        assert game.round == 0
    
    def test_setup_transitions_to_ready(self):
        game = TrivialGame()
        handler = TrivialGameHandler()
        
        handler.setup(game)
        
        assert game.phase == GamePhase.READY
        assert game.round == 0
        assert game.opponent_next_move is not None  # Pre-selected
    
    def test_receive_move_increments_round(self):
        game = TrivialGame()
        handler = TrivialGameHandler()
        handler.setup(game)
        
        handler.receive_move(game, TrivialMove.WIN)
        
        assert game.round == 1
        assert len(game.history) == 1
    
    def test_receive_move_without_setup_raises(self):
        game = TrivialGame()
        handler = TrivialGameHandler()
        
        with pytest.raises(RuntimeError, match="PENDING"):
            handler.receive_move(game, TrivialMove.WIN)
    
    def test_reset_clears_state(self):
        game = TrivialGame()
        handler = TrivialGameHandler()
        handler.setup(game)
        handler.receive_move(game, TrivialMove.WIN)
        
        # Now reset
        game.reset()
        
        assert game.phase == GamePhase.PENDING
        assert game.round == 0
        assert game.history == []
        assert game.score == {"player": 0, "opponent": 0}


class TestTrivialGame:
    """Test the trivial game implementation."""
    
    def test_player_wins_round(self):
        # Use opponent that won't pick WIN (to avoid draw)
        game = TrivialGame(opponent_strategy="trivial_lose")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        result = handler.receive_move(game, TrivialMove.WIN)
        
        assert result == RoundResult.WIN
        assert game.score["player"] == 2
        assert game.score["opponent"] == 0
    
    def test_player_loses_round(self):
        # Use opponent that picks WIN (different from player's LOSE)
        game = TrivialGame(opponent_strategy="trivial_win")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        result = handler.receive_move(game, TrivialMove.LOSE)
        
        assert result == RoundResult.LOSE
        assert game.score["player"] == 0
        assert game.score["opponent"] == 2
    
    def test_draw_round(self):
        game = TrivialGame(opponent_strategy="trivial_draw")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        result = handler.receive_move(game, TrivialMove.DRAW)
        
        # Both picked DRAW - scores increment equally
        assert result == RoundResult.DRAW
        assert game.score["player"] == game.score["opponent"]
    
    def test_win_game_best_of_three(self):
        # Use deterministic opponent to avoid random draws
        game = TrivialGame(scoring_n=3, opponent_strategy="trivial_lose")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        # Win twice to win best of 3
        handler.receive_move(game, TrivialMove.WIN)
        assert game.result == GameResult.IN_PROCESS
        assert game.phase == GamePhase.READY
        
        handler.receive_move(game, TrivialMove.WIN)
        assert game.result == GameResult.WIN
        assert game.phase == GamePhase.TERMINAL
    
    def test_lose_game_best_of_three(self):
        # Use deterministic opponent
        game = TrivialGame(scoring_n=3, opponent_strategy="trivial_win")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        handler.receive_move(game, TrivialMove.LOSE)
        handler.receive_move(game, TrivialMove.LOSE)
        
        assert game.result == GameResult.LOSE
        assert game.phase == GamePhase.TERMINAL
    
    def test_draw_game_after_all_rounds(self):
        # For a draw in best_of_2, we need 1 win and 1 loss
        # Use trivial_draw so:
        #   WIN vs DRAW → player wins
        #   LOSE vs DRAW → player loses
        game = TrivialGame(
            scoring_n=2,
            opponent_strategy="trivial_draw",
        )
        handler = TrivialGameHandler()
        handler.setup(game)
        
        # Win one, lose one
        handler.receive_move(game, TrivialMove.WIN)   # Player wins (WIN vs DRAW)
        handler.receive_move(game, TrivialMove.LOSE)  # Player loses (LOSE vs DRAW)
        
        # After 2 rounds with 1 win, 1 loss → draw
        assert game.result == GameResult.DRAW


class TestRpsGame:
    """Test rock-paper-scissors implementation."""
    
    def test_rock_beats_scissors(self):
        game = RpsGame(opponent_strategy="rps_scissors")
        handler = RpsGameHandler()
        handler.setup(game)
        
        result = handler.receive_move(game, RpsMove.ROCK)
        
        assert result == RoundResult.WIN
    
    def test_scissors_beats_paper(self):
        game = RpsGame(opponent_strategy="rps_paper")
        handler = RpsGameHandler()
        handler.setup(game)
        
        result = handler.receive_move(game, RpsMove.SCISSORS)
        
        assert result == RoundResult.WIN
    
    def test_paper_beats_rock(self):
        game = RpsGame(opponent_strategy="rps_rock")
        handler = RpsGameHandler()
        handler.setup(game)
        
        result = handler.receive_move(game, RpsMove.PAPER)
        
        assert result == RoundResult.WIN
    
    def test_same_move_is_draw(self):
        game = RpsGame(opponent_strategy="rps_rock")
        handler = RpsGameHandler()
        handler.setup(game)
        
        result = handler.receive_move(game, RpsMove.ROCK)
        
        assert result == RoundResult.DRAW
    
    def test_circular_dominance_complete(self):
        """Verify all dominance relationships."""
        handler = RpsGameHandler()
        
        # Each move should beat exactly one other
        assert handler.BEATS[RpsMove.ROCK] == RpsMove.SCISSORS
        assert handler.BEATS[RpsMove.SCISSORS] == RpsMove.PAPER
        assert handler.BEATS[RpsMove.PAPER] == RpsMove.ROCK
        
        # Each move should lose to exactly one other
        assert handler.LOSES_TO[RpsMove.ROCK] == RpsMove.PAPER
        assert handler.LOSES_TO[RpsMove.SCISSORS] == RpsMove.ROCK
        assert handler.LOSES_TO[RpsMove.PAPER] == RpsMove.SCISSORS


class TestOpponentStrategies:
    """Test opponent strategy registration and execution."""
    
    def test_strategy_registry_contains_builtins(self):
        assert "random" in opponent_strategies
        assert "rps_random" in opponent_strategies
        assert "trivial_random" in opponent_strategies
    
    def test_counter_strategy_forces_loss(self):
        game = RpsGame(
            opponent_strategy="rps_random",
            opponent_revision_strategy="rps_counter",  # Cheating!
        )
        handler = RpsGameHandler()
        handler.setup(game)
        
        # No matter what we play, opponent counters
        for move in RpsMove:
            handler.setup(game)  # Reset each time
            result = handler.receive_move(game, move)
            assert result == RoundResult.LOSE
    
    def test_throw_strategy_forces_win(self):
        game = RpsGame(
            opponent_strategy="rps_random",
            opponent_revision_strategy="rps_throw",  # Narrative victory
        )
        handler = RpsGameHandler()
        handler.setup(game)
        
        # No matter what we play, opponent throws
        for move in RpsMove:
            handler.setup(game)
            result = handler.receive_move(game, move)
            assert result == RoundResult.WIN
    
    def test_tit_for_tat_copies_previous(self):
        game = RpsGame(opponent_strategy="rps_tit_for_tat")
        handler = RpsGameHandler()
        handler.setup(game)
        
        # First move - opponent plays random (no history)
        handler.receive_move(game, RpsMove.ROCK)
        
        # Second move - opponent should play ROCK (copying us)
        assert game.opponent_next_move == RpsMove.ROCK


class TestScoringStrategies:
    """Test scoring strategy registration and execution."""
    
    def test_best_of_n_needs_majority(self):
        # Use deterministic opponent
        game = TrivialGame(scoring_n=5, scoring_strategy="best_of_n", opponent_strategy="trivial_lose")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        # Win 2 - not enough
        handler.receive_move(game, TrivialMove.WIN)
        handler.receive_move(game, TrivialMove.WIN)
        assert game.result == GameResult.IN_PROCESS
        
        # Win 3 - majority of 5
        handler.receive_move(game, TrivialMove.WIN)
        assert game.result == GameResult.WIN
    
    def test_first_to_n_stops_at_threshold(self):
        # Use deterministic opponent to avoid random draws
        game = TrivialGame(scoring_n=4, scoring_strategy="first_to_n", opponent_strategy="trivial_lose")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        # Each WIN gives 2 points, need 4
        handler.receive_move(game, TrivialMove.WIN)  # 2 points
        assert game.result == GameResult.IN_PROCESS
        
        handler.receive_move(game, TrivialMove.WIN)  # 4 points
        assert game.result == GameResult.WIN
    
    def test_single_round_ends_immediately(self):
        # Use deterministic opponent
        game = TrivialGame(scoring_strategy="single_round", opponent_strategy="trivial_lose")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        handler.receive_move(game, TrivialMove.WIN)
        
        assert game.result == GameResult.WIN
        assert game.phase == GamePhase.TERMINAL


class TestRpslsGame:
    """Test Rock-Paper-Scissors-Lizard-Spock."""
    
    def test_spock_vaporizes_rock(self):
        game = RpslsGame(opponent_strategy="rpsls_random")
        game.opponent_next_move = RpslsMove.ROCK  # Force opponent move
        handler = RpslsGameHandler()
        handler.setup(game)
        game.opponent_next_move = RpslsMove.ROCK  # Re-force after setup
        
        result = handler.receive_move(game, RpslsMove.SPOCK)
        assert result == RoundResult.WIN
    
    def test_lizard_eats_paper(self):
        game = RpslsGame()
        handler = RpslsGameHandler()
        handler.setup(game)
        game.opponent_next_move = RpslsMove.PAPER
        
        result = handler.receive_move(game, RpslsMove.LIZARD)
        assert result == RoundResult.WIN
    
    def test_each_move_beats_two(self):
        handler = RpslsGameHandler()
        
        for move in RpslsMove:
            beaten = handler.BEATS[move]
            assert len(beaten) == 2, f"{move} should beat exactly 2 moves"


class TestGameNamespace:
    """Test namespace export for condition evaluation."""
    
    def test_namespace_contains_result_enum(self):
        game = TrivialGame()
        ns = game.to_namespace()
        
        assert "GameResult" in ns
        assert "R" in ns  # Short alias
        assert ns["R"] is GameResult
    
    def test_namespace_reflects_game_state(self):
        game = TrivialGame(opponent_strategy="trivial_lose")  # Deterministic
        handler = TrivialGameHandler()
        handler.setup(game)
        
        ns = game.to_namespace()
        assert ns["game_is_ready"] is True
        assert ns["game_is_terminal"] is False
        assert ns["game_in_progress"] is True
        
        # Play to terminal
        handler.receive_move(game, TrivialMove.WIN)
        handler.receive_move(game, TrivialMove.WIN)
        
        ns = game.to_namespace()
        assert ns["game_is_terminal"] is True
        assert ns["player_won_game"] is True
    
    def test_namespace_includes_last_round(self):
        game = RpsGame(opponent_strategy="rps_scissors")
        handler = RpsGameHandler()
        handler.setup(game)
        handler.receive_move(game, RpsMove.ROCK)
        
        ns = game.to_namespace()
        
        assert ns["last_player_move"] == RpsMove.ROCK
        assert ns["last_opponent_move"] == RpsMove.SCISSORS
        assert ns["player_won_round"] is True


class TestHistory:
    """Test game history tracking."""
    
    def test_history_records_all_rounds(self):
        # Use trivial_lose so player's moves produce predictable outcomes
        game = TrivialGame(scoring_n=5, opponent_strategy="trivial_lose")
        handler = TrivialGameHandler()
        handler.setup(game)
        
        handler.receive_move(game, TrivialMove.WIN)   # Player wins (vs LOSE)
        handler.receive_move(game, TrivialMove.LOSE)  # Player loses (vs LOSE = DRAW)
        handler.receive_move(game, TrivialMove.DRAW)  # Draw (vs LOSE)
        
        assert len(game.history) == 3
        
        assert game.history[0].player_move == TrivialMove.WIN
        assert game.history[0].result == RoundResult.WIN
        
        # LOSE vs LOSE = both pick same = DRAW
        assert game.history[1].player_move == TrivialMove.LOSE
        assert game.history[1].result == RoundResult.DRAW
    
    def test_history_includes_round_numbers(self):
        game = TrivialGame(opponent_strategy="trivial_lose")  # Deterministic
        handler = TrivialGameHandler()
        handler.setup(game)
        
        handler.receive_move(game, TrivialMove.WIN)
        handler.receive_move(game, TrivialMove.WIN)
        
        assert game.history[0].round_number == 1
        assert game.history[1].round_number == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
