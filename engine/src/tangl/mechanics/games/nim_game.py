"""
Nim-style token depletion over fungible heaps.

A single scalar heap is an appealing trap: it is the one configuration of this
family that is already solved. With takes bounded at ``k``, a heap of size ``n``
is a first-player win exactly when ``n % (k + 1) != 0``, so a single-heap board
has no strategy left in it once anyone notices.

The interesting cases arrive as soon as there is more than one heap, or more
than one kind of token, and both are the same generalization: **a heap is a
token type in a wallet.** ``{"heap": 7}`` is one-heap Nim; ``{"red": 5,
"blue": 3}`` is a two-colour contest where the two piles deplete
independently. No extra structure is needed for either.

Bounded multi-heap Nim is genuinely strategic. The Grundy value of a heap of
size ``n`` under a take bound ``k`` is ``n % (k + 1)``, and a position is lost
for the mover exactly when those values XOR to zero — which is what
``nim_optimal`` plays.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from operator import xor
import random
from typing import ClassVar

from pydantic import Field

from tangl.journal.intent import QuantityAccepts
from tangl.journal.fragments import ContentFragment
from tangl.story.concepts.asset import AssetWallet
from tangl.vm.ctx import VmPhaseCtx

from .enums import RoundResult
from .game import Game
from .handler import GameHandler
from .strategies import opponent_strategies

#: Heap label used when a game does not name its piles.
DEFAULT_HEAP = "heap"


@dataclass(frozen=True)
class NimMove:
    """Take ``count`` tokens from the pile named ``pile``."""

    pile: str
    count: int

    @property
    def is_selector(self) -> bool:
        """True for the provisioned pile-selector placeholder."""

        return self.count == 0


class NimGame(Game[NimMove]):
    """State for a bounded Nim contest over one or more token heaps."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = "nim_random"

    #: Opening heap contents, keyed by token label. One entry is classic Nim.
    opening_heaps: dict[str, int] = Field(default_factory=lambda: {DEFAULT_HEAP: 7})
    min_take: int = 1
    max_take: int = 3
    last_token_wins: bool = True
    shuffle_seed: int | None = None

    heaps: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    @property
    def total_tokens(self) -> int:
        """Return the number of tokens remaining across every heap."""

        return sum(count for _, count in self.heaps.items())

    def pile_labels(self) -> list[str]:
        """Return non-empty heap labels in stable order."""

        return sorted(label for label, count in self.heaps.items() if count > 0)

    def get_available_moves(self) -> list[NimMove]:
        moves: list[NimMove] = []
        for label in self.pile_labels():
            upper = min(self.max_take, self.heaps[label])
            moves.extend(
                NimMove(pile=label, count=count)
                for count in range(self.min_take, upper + 1)
            )
        return moves

    def grundy_values(self) -> list[int]:
        """Return each heap's Grundy value under the current take bound."""

        modulus = self.max_take + 1
        return [self.heaps[label] % modulus for label in self.pile_labels()]

    @property
    def is_losing_position(self) -> bool:
        """True when the player to move has no forced win under optimal play."""

        values = self.grundy_values()
        if not values:
            return True
        return reduce(xor, values) == 0

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "nim_heaps": dict(self.heaps.amounts),
                "nim_total": self.total_tokens,
                "nim_pile_count": len(self.pile_labels()),
                "nim_min_take": self.min_take,
                "nim_max_take": self.max_take,
                "nim_last_token_wins": self.last_token_wins,
                "nim_is_losing_position": self.is_losing_position,
                "nim_opponent_next_take": self.opponent_next_move,
            }
        )
        return namespace


class NimGameHandler(GameHandler[NimGame]):
    """Handler for narrated bounded Nim over token heaps."""

    game_cls: ClassVar[type[Game]] = NimGame

    def on_setup(self, game: NimGame) -> None:
        game.heaps = AssetWallet()
        game.heaps.gain({
            label: count
            for label, count in game.opening_heaps.items()
            if count > 0
        })
        game.round_detail = {
            "heaps_before": dict(game.heaps.amounts),
            "outcome": "opening",
        }

    def get_available_moves(self, game: NimGame) -> list[NimMove]:
        return game.get_available_moves()

    def get_provisioned_moves(self, game: NimGame) -> list[NimMove]:
        # One quantity selector per non-empty heap.
        return [NimMove(pile=label, count=0) for label in game.pile_labels()]

    def get_move_label(self, game: NimGame, move: NimMove) -> str:
        multi = len(game.pile_labels()) > 1
        where = f" from {move.pile}" if multi else ""
        if move.is_selector:
            return f"Take tokens{where}" if multi else "Take tokens"
        noun = "token" if move.count == 1 else "tokens"
        return f"Take {move.count} {noun}{where}"

    def get_move_accepts(self, game: NimGame, move: NimMove) -> QuantityAccepts | None:
        if not move.is_selector:
            return None
        return QuantityAccepts(
            min=game.min_take,
            max=min(game.max_take, game.heaps[move.pile]),
            unit="token",
        )

    def resolve_move_payload(
        self,
        game: NimGame,
        move: NimMove,
        payload: dict[str, object],
    ) -> NimMove:
        if not move.is_selector:
            return move

        quantity = payload.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("Take tokens requires an integer quantity")
        resolved = NimMove(pile=move.pile, count=quantity)
        if resolved not in game.get_available_moves():
            raise ValueError(f"Invalid take: {quantity} from {move.pile}")
        return resolved

    def resolve_round(
        self,
        game: NimGame,
        player_move: NimMove,
        opponent_move: NimMove | None,
    ) -> RoundResult:
        detail: dict[str, object] = {
            "heaps_before": dict(game.heaps.amounts),
            "player_take": player_move.count,
            "player_pile": player_move.pile,
        }

        game.heaps.spend({player_move.pile: player_move.count})
        detail["heaps_after_player"] = dict(game.heaps.amounts)

        if game.total_tokens <= 0:
            result = RoundResult.WIN if game.last_token_wins else RoundResult.LOSE
            self._score_terminal(game, result)
            detail["outcome"] = result.value
            game.round_detail = detail
            return result

        if opponent_move is None:
            detail["outcome"] = "continue"
            game.round_detail = detail
            return RoundResult.CONTINUE

        game.heaps.spend({opponent_move.pile: opponent_move.count})
        detail["opponent_take"] = opponent_move.count
        detail["opponent_pile"] = opponent_move.pile
        detail["heaps_after_opponent"] = dict(game.heaps.amounts)

        if game.total_tokens <= 0:
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
        player_move: NimMove,
        opponent_move: NimMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["heaps_remaining"] = dict(game.heaps.amounts)
        detail["total_remaining"] = game.total_tokens
        detail["opponent_next_take"] = game.opponent_next_move
        return detail

    def get_journal_fragments(
        self,
        game: NimGame,
        *,
        ctx: VmPhaseCtx | None = None,
    ) -> list[ContentFragment] | None:
        _ = ctx
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        multi = len(game.opening_heaps) > 1

        def _where(pile: object) -> str:
            return f" from {pile}" if multi and pile else ""

        fragments = [
            ContentFragment(
                content=f"You take {notes.get('player_take', 0)}{_where(notes.get('player_pile'))}."
            )
        ]

        opponent_take = notes.get("opponent_take")
        if opponent_take is not None:
            fragments.append(
                ContentFragment(
                    content=(
                        f"Your opponent takes {opponent_take}"
                        f"{_where(notes.get('opponent_pile'))}."
                    )
                )
            )

        if last_round.result == RoundResult.CONTINUE:
            remaining = notes.get("heaps_remaining") or {}
            if multi:
                summary = ", ".join(
                    f"{count} in {label}"
                    for label, count in sorted(remaining.items())
                    if count > 0
                )
                fragments.append(ContentFragment(content=f"Remaining: {summary}."))
            else:
                fragments.append(
                    ContentFragment(
                        content=f"{notes.get('total_remaining', game.total_tokens)} tokens remain in the heap."
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
def _nim_random(game: NimGame, **ctx) -> NimMove:
    randomizer = random.Random(game.shuffle_seed)
    return randomizer.choice(game.get_available_moves())


@opponent_strategies.register("nim_greedy")
def _nim_greedy(game: NimGame, **ctx) -> NimMove:
    return max(game.get_available_moves(), key=lambda move: move.count)


@opponent_strategies.register("nim_optimal")
def _nim_optimal(game: NimGame, **ctx) -> NimMove:
    """Play the bounded-Nim Grundy move, leaving a zero XOR when one exists.

    Falls back to the smallest legal take from the largest heap when the
    position is already lost, which is the move that gives an imperfect
    opponent the most chances to err.
    """

    modulus = game.max_take + 1
    moves = game.get_available_moves()

    for move in moves:
        residuals = []
        for label in game.pile_labels():
            remaining = game.heaps[label] - (move.count if label == move.pile else 0)
            residuals.append(remaining % modulus)
        if residuals and reduce(xor, residuals) == 0:
            return move

    largest = max(game.pile_labels(), key=lambda label: game.heaps[label])
    return NimMove(pile=largest, count=game.min_take)


#: Retained for single-heap boards, where the Grundy move reduces to this.
opponent_strategies.register_func(_nim_optimal, "nim_safe")
