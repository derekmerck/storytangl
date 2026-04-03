"""
Nim-style token depletion contest.

This stays intentionally small: one heap, bounded takes, one opponent policy
slot, and one terminal rule toggle for whether taking the last token wins.
"""
from __future__ import annotations

import random
from typing import ClassVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment

from .enums import RoundResult
from .game import Game
from .handler import GameHandler
from .strategies import opponent_strategies


class NimGame(Game[int]):
    """State for a one-heap Nim-style contest."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = "nim_random"

    opening_heap_size: int = 7
    min_take: int = 1
    max_take: int = 3
    last_token_wins: bool = True
    shuffle_seed: int | None = None

    heap_size: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    def get_available_moves(self) -> list[int]:
        upper = min(self.max_take, self.heap_size)
        if upper < self.min_take:
            return []
        return list(range(self.min_take, upper + 1))

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "nim_heap_size": self.heap_size,
                "nim_min_take": self.min_take,
                "nim_max_take": self.max_take,
                "nim_last_token_wins": self.last_token_wins,
                "nim_opponent_next_take": self.opponent_next_move,
            }
        )
        return namespace


class NimGameHandler(GameHandler[NimGame]):
    """Small handler for narrated one-heap Nim contests."""

    game_cls: ClassVar[type[Game]] = NimGame

    def on_setup(self, game: NimGame) -> None:
        game.heap_size = game.opening_heap_size
        game.round_detail = {
            "heap_before": game.heap_size,
            "outcome": "opening",
        }

    def get_available_moves(self, game: NimGame) -> list[int]:
        return game.get_available_moves()

    def get_move_label(self, game: NimGame, move: int) -> str:
        noun = "token" if move == 1 else "tokens"
        return f"Take {move} {noun}"

    def resolve_round(
        self,
        game: NimGame,
        player_move: int,
        opponent_move: int | None,
    ) -> RoundResult:
        detail: dict[str, object] = {
            "heap_before": game.heap_size,
            "player_take": player_move,
        }

        game.heap_size -= player_move
        detail["heap_after_player"] = game.heap_size

        if game.heap_size <= 0:
            result = RoundResult.WIN if game.last_token_wins else RoundResult.LOSE
            self._score_terminal(game, result)
            detail["outcome"] = result.value
            game.round_detail = detail
            return result

        if opponent_move is None:
            detail["outcome"] = "continue"
            game.round_detail = detail
            return RoundResult.CONTINUE

        game.heap_size -= opponent_move
        detail["opponent_take"] = opponent_move
        detail["heap_after_opponent"] = game.heap_size

        if game.heap_size <= 0:
            result = RoundResult.LOSE if game.last_token_wins else RoundResult.WIN
            self._score_terminal(game, result)
            detail["outcome"] = result.value
            game.round_detail = detail
            return result

        detail["outcome"] = "continue"
        game.round_detail = detail
        return RoundResult.CONTINUE

    def build_round_notes(
        self,
        game: NimGame,
        player_move: int,
        opponent_move: int | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["heap_remaining"] = game.heap_size
        detail["opponent_next_take"] = game.opponent_next_move
        return detail

    def get_journal_fragments(self, game: NimGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        fragments = [
            ContentFragment(content=f"You take {notes.get('player_take', 0)}."),
        ]

        opponent_take = notes.get("opponent_take")
        if opponent_take is not None:
            fragments.append(ContentFragment(content=f"Your opponent takes {opponent_take}."))

        if last_round.result == RoundResult.CONTINUE:
            fragments.append(
                ContentFragment(
                    content=f"{notes.get('heap_remaining', game.heap_size)} tokens remain in the heap."
                )
            )
            return fragments

        end_line = {
            RoundResult.WIN: "The heap collapses in your favor.",
            RoundResult.LOSE: "The final token turns the room against you.",
            RoundResult.DRAW: "The heap resolves without a clear victor.",
        }[last_round.result]
        fragments.append(ContentFragment(content=end_line))
        return fragments

    def _score_terminal(self, game: NimGame, result: RoundResult) -> None:
        if result == RoundResult.WIN:
            game.score["player"] = 1
        elif result == RoundResult.LOSE:
            game.score["opponent"] = 1
        else:
            game.score["player"] = 1
            game.score["opponent"] = 1


@opponent_strategies.register("nim_random")
def _nim_random(game: NimGame, **ctx) -> int:
    randomizer = random.Random(game.shuffle_seed)
    return randomizer.choice(game.get_available_moves())


@opponent_strategies.register("nim_greedy")
def _nim_greedy(game: NimGame, **ctx) -> int:
    return max(game.get_available_moves())


@opponent_strategies.register("nim_safe")
def _nim_safe(game: NimGame, **ctx) -> int:
    moves = game.get_available_moves()
    target = game.max_take + 1
    preferred = game.heap_size % target
    if preferred in moves:
        return preferred
    return min(moves)
