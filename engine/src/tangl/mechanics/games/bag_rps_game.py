"""
Bag-RPS aggregate-force contest.

Each side commits a bounded mixed profile from a reserve of rock, paper, and
scissors tokens. Attrition depends on composition rather than a single throw.
"""
from __future__ import annotations

import random
from typing import ClassVar

from pydantic import Field

from tangl.mechanics.games.strategies import opponent_strategies

from .aggregate_force_game import AggregateForceGame, AggregateForceGameHandler, ForceCommitMove
from .game import Game


class BagRpsGame(AggregateForceGame):
    """Concrete aggregate-force RPS contest."""

    force_types: list[str] = Field(default_factory=lambda: ["rock", "paper", "scissors"])
    force_beats: dict[str, str] = Field(
        default_factory=lambda: {
            "rock": "scissors",
            "paper": "rock",
            "scissors": "paper",
        }
    )
    force_weights: dict[str, int] = Field(
        default_factory=lambda: {
            "rock": 1,
            "paper": 1,
            "scissors": 1,
        }
    )
    player_opening_reserve: dict[str, int] = Field(
        default_factory=lambda: {
            "rock": 2,
            "paper": 1,
            "scissors": 1,
        }
    )
    opponent_opening_reserve: dict[str, int] = Field(
        default_factory=lambda: {
            "rock": 1,
            "paper": 2,
            "scissors": 1,
        }
    )
    shuffle_seed: int | None = None

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "bag_rps_player_reserve": dict(self.player_reserve),
                "bag_rps_opponent_reserve": dict(self.opponent_reserve),
            }
        )
        return namespace


class BagRpsGameHandler(AggregateForceGameHandler[BagRpsGame]):
    """Concrete handler for the first aggregate-force contest variant."""

    game_cls: ClassVar[type[Game]] = BagRpsGame


@opponent_strategies.register("aggregate_force_greedy")
def _aggregate_force_greedy(game: AggregateForceGame, **ctx) -> ForceCommitMove | None:
    handler = AggregateForceGameHandler()
    moves = handler._profiles_for_reserve(game, game.opponent_reserve)
    if not moves:
        return None
    return max(
        moves,
        key=lambda move: (
            move.total_units,
            len(move.profile),
            tuple(label for label, _ in move.profile),
        ),
    )


@opponent_strategies.register("aggregate_force_random")
def _aggregate_force_random(game: AggregateForceGame, **ctx) -> ForceCommitMove | None:
    handler = AggregateForceGameHandler()
    moves = handler._profiles_for_reserve(game, game.opponent_reserve)
    if not moves:
        return None
    chooser = random.Random(getattr(game, "shuffle_seed", None))
    return chooser.choice(moves)
