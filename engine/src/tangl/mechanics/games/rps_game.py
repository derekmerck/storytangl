"""
Rock-Paper-Scissors game implementation.

The classic state-independent game demonstrating:
- Circular dominance (rock beats scissors beats paper beats rock)
- Opponent pre-selection and revision strategies
- Various scoring strategies
"""
from __future__ import annotations
from enum import Enum
from typing import ClassVar, Type
import random

from pydantic import Field

from tangl.journal.content import ContentFragment
from tangl.vm.dispatch import vm_dispatch

from .enums import GamePhase, GameResult, RoundResult
from .game import Game, RoundRecord
from .handler import GameHandler, SimpleGameHandler
from .strategies import opponent_strategies, scoring_strategies


class RpsMove(Enum):
    """Standard rock-paper-scissors moves."""
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


class RpsGame(Game[RpsMove]):
    """
    Game state for Rock-Paper-Scissors.
    
    Default configuration: best of 3 rounds.
    """
    scoring_n: int = 3
    scoring_strategy: str = "best_of_n"
    opponent_strategy: str = "rps_random"


class RpsGameHandler(SimpleGameHandler[RpsGame]):
    """
    Handler for Rock-Paper-Scissors.
    
    Uses circular dominance: each move beats exactly one other move.
    """
    
    moves: ClassVar[list[RpsMove]] = list(RpsMove)
    game_cls: ClassVar[Type[Game]] = RpsGame
    
    # Dominance mapping: move -> what it beats
    BEATS: ClassVar[dict[RpsMove, RpsMove]] = {
        RpsMove.ROCK: RpsMove.SCISSORS,
        RpsMove.PAPER: RpsMove.ROCK,
        RpsMove.SCISSORS: RpsMove.PAPER,
    }
    
    # Inverse: move -> what beats it
    LOSES_TO: ClassVar[dict[RpsMove, RpsMove]] = {
        v: k for k, v in BEATS.items()
    }
    
    def resolve_round(
        self,
        game: RpsGame,
        player_move: RpsMove,
        opponent_move: RpsMove | None,
    ) -> RoundResult:
        """
        Resolve RPS round using circular dominance.
        """
        if opponent_move is None:
            # No opponent - player wins by default
            game.score["player"] += 1
            return RoundResult.WIN
        
        if player_move == opponent_move:
            # Draw - no score change
            return RoundResult.DRAW
        
        if self.BEATS[player_move] == opponent_move:
            # Player wins
            game.score["player"] += 1
            return RoundResult.WIN
        else:
            # Opponent wins
            game.score["opponent"] += 1
            return RoundResult.LOSE


# ─────────────────────────────────────────────────────────────────────────────
# Opponent strategies for RPS
# ─────────────────────────────────────────────────────────────────────────────

@opponent_strategies.register("rps_random")
def _rps_random(game: RpsGame, **ctx) -> RpsMove:
    """Random RPS move."""
    return random.choice(list(RpsMove))


@opponent_strategies.register("rps_rock")
def _rps_always_rock(game: RpsGame, **ctx) -> RpsMove:
    """Predictable opponent - always rock."""
    return RpsMove.ROCK


@opponent_strategies.register("rps_paper")
def _rps_always_paper(game: RpsGame, **ctx) -> RpsMove:
    """Predictable opponent - always paper."""
    return RpsMove.PAPER


@opponent_strategies.register("rps_scissors")
def _rps_always_scissors(game: RpsGame, **ctx) -> RpsMove:
    """Predictable opponent - always scissors."""
    return RpsMove.SCISSORS


@opponent_strategies.register("rps_cycle")
def _rps_cycle(game: RpsGame, **ctx) -> RpsMove:
    """Cycle through R-P-S based on round number."""
    moves = [RpsMove.ROCK, RpsMove.PAPER, RpsMove.SCISSORS]
    return moves[game.round % 3]


@opponent_strategies.register("rps_counter")
def _rps_counter(game: RpsGame, player_move: RpsMove = None, **ctx) -> RpsMove:
    """
    Revision strategy: counter the player's move (forces player loss).
    
    This is the "cheating" opponent for narrative purposes.
    """
    if player_move is None:
        return random.choice(list(RpsMove))
    # Return what beats the player's move
    return RpsGameHandler.LOSES_TO[player_move]


@opponent_strategies.register("rps_throw")
def _rps_throw(game: RpsGame, player_move: RpsMove = None, **ctx) -> RpsMove:
    """
    Revision strategy: lose to the player's move (forces player win).
    
    For when the narrative demands victory.
    """
    if player_move is None:
        return random.choice(list(RpsMove))
    # Return what the player's move beats
    return RpsGameHandler.BEATS[player_move]


@opponent_strategies.register("rps_tit_for_tat")
def _rps_tit_for_tat(game: RpsGame, **ctx) -> RpsMove:
    """
    Copy the player's previous move.
    
    Classic game theory strategy. First move is random.
    """
    if not game.history:
        return random.choice(list(RpsMove))
    return game.history[-1].player_move


# ─────────────────────────────────────────────────────────────────────────────
# Extended RPS: Rock-Paper-Scissors-Lizard-Spock
# ─────────────────────────────────────────────────────────────────────────────

class RpslsMove(Enum):
    """
    Rock-Paper-Scissors-Lizard-Spock moves.
    
    Each move beats two others:
    - Rock crushes Scissors, crushes Lizard
    - Paper covers Rock, disproves Spock
    - Scissors cuts Paper, decapitates Lizard
    - Lizard poisons Spock, eats Paper
    - Spock smashes Scissors, vaporizes Rock
    """
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"
    LIZARD = "lizard"
    SPOCK = "spock"


class RpslsGame(Game[RpslsMove]):
    """Game state for RPSLS."""
    scoring_n: int = 5
    scoring_strategy: str = "best_of_n"
    opponent_strategy: str = "rpsls_random"


class RpslsGameHandler(SimpleGameHandler[RpslsGame]):
    """
    Handler for Rock-Paper-Scissors-Lizard-Spock.
    
    Extended dominance: each move beats two others.
    """
    
    moves: ClassVar[list[RpslsMove]] = list(RpslsMove)
    game_cls: ClassVar[Type[Game]] = RpslsGame
    
    # Each move beats these two
    BEATS: ClassVar[dict[RpslsMove, list[RpslsMove]]] = {
        RpslsMove.ROCK: [RpslsMove.SCISSORS, RpslsMove.LIZARD],
        RpslsMove.PAPER: [RpslsMove.ROCK, RpslsMove.SPOCK],
        RpslsMove.SCISSORS: [RpslsMove.PAPER, RpslsMove.LIZARD],
        RpslsMove.LIZARD: [RpslsMove.SPOCK, RpslsMove.PAPER],
        RpslsMove.SPOCK: [RpslsMove.SCISSORS, RpslsMove.ROCK],
    }
    
    def resolve_round(
        self,
        game: RpslsGame,
        player_move: RpslsMove,
        opponent_move: RpslsMove | None,
    ) -> RoundResult:
        """Resolve RPSLS round."""
        if opponent_move is None:
            game.score["player"] += 1
            return RoundResult.WIN
        
        if player_move == opponent_move:
            return RoundResult.DRAW
        
        if opponent_move in self.BEATS[player_move]:
            game.score["player"] += 1
            return RoundResult.WIN
        else:
            game.score["opponent"] += 1
            return RoundResult.LOSE


@opponent_strategies.register("rpsls_random")
def _rpsls_random(game: RpslsGame, **ctx) -> RpslsMove:
    """Random RPSLS move."""
    return random.choice(list(RpslsMove))


RPS_VERB_TEMPLATES: dict[tuple[RpsMove, RpsMove], str] = {
    (RpsMove.ROCK, RpsMove.SCISSORS): "{player} crushes {opponent}",
    (RpsMove.SCISSORS, RpsMove.PAPER): "{player} cuts {opponent}",
    (RpsMove.PAPER, RpsMove.ROCK): "{player} covers {opponent}",
}


RPSLS_VERB_TEMPLATES: dict[tuple[RpslsMove, RpslsMove], str] = {
    (RpslsMove.ROCK, RpslsMove.SCISSORS): "{player} crushes {opponent}",
    (RpslsMove.ROCK, RpslsMove.LIZARD): "{player} crushes {opponent}",
    (RpslsMove.PAPER, RpslsMove.ROCK): "{player} covers {opponent}",
    (RpslsMove.PAPER, RpslsMove.SPOCK): "{player} disproves {opponent}",
    (RpslsMove.SCISSORS, RpslsMove.PAPER): "{player} cuts {opponent}",
    (RpslsMove.SCISSORS, RpslsMove.LIZARD): "{player} decapitates {opponent}",
    (RpslsMove.LIZARD, RpslsMove.PAPER): "{player} eats {opponent}",
    (RpslsMove.LIZARD, RpslsMove.SPOCK): "{player} poisons {opponent}",
    (RpslsMove.SPOCK, RpslsMove.ROCK): "{player} vaporizes {opponent}",
    (RpslsMove.SPOCK, RpslsMove.SCISSORS): "{player} smashes {opponent}",
}


@vm_dispatch.register(task="generate_journal", caller=RpsGame)
def rps_generate_journal(game: RpsGame, *, ctx, **kwargs) -> list[ContentFragment]:
    """Generate Rock–Paper–Scissors journal fragments."""

    if not isinstance(game, RpsGame):
        return None

    if not game.history:
        return None

    last_round = game.history[-1]
    fragments: list[ContentFragment] = [
        ContentFragment(content=f"**Round {last_round.round_number} of {game.scoring_n}**")
    ]

    player_move = last_round.player_move
    opponent_move = last_round.opponent_move

    if opponent_move is None:
        narrative = "Opponent forfeited."
    elif last_round.result == RoundResult.DRAW:
        narrative = f"Both play {player_move.value}. Draw!"
    elif last_round.result == RoundResult.WIN:
        template = RPS_VERB_TEMPLATES.get((player_move, opponent_move))
        verb_line = (
            template.format(
                player=player_move.value.capitalize(),
                opponent=opponent_move.value,
            )
            if template
            else f"{player_move.value.capitalize()} beats {opponent_move.value}"
        )
        narrative = f"{verb_line} You won this round!"
    else:
        template = RPS_VERB_TEMPLATES.get((opponent_move, player_move))
        verb_line = (
            template.format(
                player=opponent_move.value.capitalize(),
                opponent=player_move.value,
            )
            if template
            else f"{opponent_move.value.capitalize()} beats {player_move.value}"
        )
        narrative = f"{verb_line} You lost this round."

    fragments.append(ContentFragment(content=narrative))

    score = game.score or {"player": 0, "opponent": 0}
    fragments.append(
        ContentFragment(
            content=f"*Score: {score.get('player', 0)}-{score.get('opponent', 0)} (first to {game.scoring_n})*"
        )
    )

    if game.opponent_next_move:
        fragments.append(
            ContentFragment(
                content=f"*Your opponent is preparing {game.opponent_next_move.value}...*"
            )
        )

    return fragments


@vm_dispatch.register(task="generate_journal", caller=RpslsGame)
def rpsls_generate_journal(game: RpslsGame, *, ctx, **kwargs) -> list[ContentFragment]:
    """Generate Rock–Paper–Scissors–Lizard–Spock journal fragments."""

    if not isinstance(game, RpslsGame):
        return None

    if not game.history:
        return None

    last_round = game.history[-1]
    fragments: list[ContentFragment] = [
        ContentFragment(content=f"**Round {last_round.round_number} of {game.scoring_n}**")
    ]

    player_move = last_round.player_move
    opponent_move = last_round.opponent_move

    if opponent_move is None:
        narrative = "Opponent forfeited."
    elif last_round.result == RoundResult.DRAW:
        narrative = f"Both play {player_move.value}. Draw!"
    elif last_round.result == RoundResult.WIN:
        template = RPSLS_VERB_TEMPLATES.get((player_move, opponent_move))
        verb_line = (
            template.format(
                player=player_move.value.capitalize(),
                opponent=opponent_move.value,
            )
            if template
            else f"{player_move.value.capitalize()} beats {opponent_move.value}"
        )
        narrative = f"{verb_line} You won this round!"
    else:
        template = RPSLS_VERB_TEMPLATES.get((opponent_move, player_move))
        verb_line = (
            template.format(
                player=opponent_move.value.capitalize(),
                opponent=player_move.value,
            )
            if template
            else f"{opponent_move.value.capitalize()} beats {player_move.value}"
        )
        narrative = f"{verb_line} You lost this round."

    fragments.append(ContentFragment(content=narrative))

    score = game.score or {"player": 0, "opponent": 0}
    fragments.append(
        ContentFragment(
            content=f"*Score: {score.get('player', 0)}-{score.get('opponent', 0)} (first to {game.scoring_n})*"
        )
    )

    if game.opponent_next_move:
        fragments.append(
            ContentFragment(
                content=f"*Your opponent is preparing {game.opponent_next_move.value}...*"
            )
        )

    return fragments
