"""
Blackjack contest implementation.

This is a narrated, house-style contest rather than a fairness-first casino
simulation. The player chooses when to hit or stand, while the dealer follows a
deterministic reveal and draw policy configured on the game state.
"""
from __future__ import annotations

from enum import Enum
import random
from typing import ClassVar

from pydantic import Field

from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import ContentFragment

from .enums import GameResult, RoundResult
from .game import Game
from .handler import GameHandler


class BlackjackMove(Enum):
    """Player actions in blackjack."""

    HIT = "hit"
    STAND = "stand"


class PlayingCard(BaseModelPlus):
    """Serializable playing card model for blackjack-style contests."""

    rank: int
    suit: str

    @property
    def short_name(self) -> str:
        rank_label = {
            1: "A",
            11: "J",
            12: "Q",
            13: "K",
        }.get(self.rank, str(self.rank))
        return f"{rank_label}{self.suit.upper()}"

    @classmethod
    def fresh_deck(cls, *, seed: int | None = None) -> list[PlayingCard]:
        """Return a shuffled 52-card deck."""

        deck = [
            cls(rank=rank, suit=suit)
            for suit in ("s", "h", "d", "c")
            for rank in range(1, 14)
        ]
        random.Random(seed).shuffle(deck)
        return deck

    @classmethod
    def hand_total(cls, cards: list[PlayingCard]) -> int:
        """Blackjack total with one soft ace when useful."""

        total = 0
        aces = 0
        for card in cards:
            if card.rank == 1:
                aces += 1
                total += 1
                continue
            total += min(card.rank, 10)

        while aces and total <= 11:
            total += 10
            aces -= 1
        return total

    def __str__(self) -> str:  # pragma: no cover - exercised via journal strings
        return self.short_name


class BlackjackGame(Game[BlackjackMove]):
    """State container for a narrated blackjack contest."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = None

    shuffle_seed: int | None = None
    deal_bias: str = "neutral"
    dealer_stand_at: int = 17
    reveal_policy: str = "upcard"

    card_deck: list[PlayingCard] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    player_hand: list[PlayingCard] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    dealer_hand: list[PlayingCard] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    player_stood: bool = Field(
        default=False,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    @property
    def player_total(self) -> int:
        return PlayingCard.hand_total(self.player_hand)

    @property
    def dealer_total(self) -> int:
        return PlayingCard.hand_total(self.dealer_hand)

    @property
    def visible_dealer_hand(self) -> list[PlayingCard]:
        if self.result.is_terminal or self.reveal_policy == "full":
            return list(self.dealer_hand)
        return list(self.dealer_hand[:1])

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "blackjack_player_total": self.player_total,
                "blackjack_player_hand": [card.short_name for card in self.player_hand],
                "blackjack_dealer_visible_total": PlayingCard.hand_total(
                    self.visible_dealer_hand
                ),
                "blackjack_dealer_visible_hand": [
                    card.short_name for card in self.visible_dealer_hand
                ],
                "blackjack_dealer_total": (
                    self.dealer_total if self.result.is_terminal or self.reveal_policy == "full" else None
                ),
                "blackjack_can_hit": self.player_total < 21 and not self.player_stood,
                "blackjack_player_stood": self.player_stood,
                "blackjack_deal_bias": self.deal_bias,
                "blackjack_reveal_policy": self.reveal_policy,
                "blackjack_dealer_stand_at": self.dealer_stand_at,
            }
        )
        if self.visible_dealer_hand:
            namespace["blackjack_dealer_upcard"] = self.visible_dealer_hand[0].short_name
        return namespace


class BlackjackGameHandler(GameHandler[BlackjackGame]):
    """Narrated blackjack handler with explicit author-tunable pressure knobs."""

    game_cls: ClassVar[type[Game]] = BlackjackGame
    OPENING_DEALS: ClassVar[dict[str, list[tuple[int, str]]]] = {
        "neutral": [],
        "player_advantage": [(10, "h"), (6, "c"), (9, "s"), (10, "d")],
        "dealer_advantage": [(5, "c"), (10, "s"), (6, "h"), (9, "d")],
        "dramatic": [(10, "h"), (9, "s"), (6, "d"), (7, "c")],
    }

    def on_setup(self, game: BlackjackGame) -> None:
        game.card_deck = PlayingCard.fresh_deck(seed=game.shuffle_seed)
        self._stack_opening_deal(game)
        game.player_hand = [self._draw_card(game)]
        game.dealer_hand = [self._draw_card(game)]
        game.player_hand.append(self._draw_card(game))
        game.dealer_hand.append(self._draw_card(game))
        game.player_stood = False
        game.round_detail = {
            "phase": "opening",
            "player_total": game.player_total,
            "dealer_visible_total": PlayingCard.hand_total(game.visible_dealer_hand),
            "dealer_upcard": game.visible_dealer_hand[0].short_name,
        }

    def get_available_moves(self, game: BlackjackGame) -> list[BlackjackMove]:
        if game.result.is_terminal or game.player_stood:
            return []
        if game.player_total >= 21:
            return [BlackjackMove.STAND]
        return [BlackjackMove.HIT, BlackjackMove.STAND]

    def get_move_label(self, game: BlackjackGame, move: BlackjackMove) -> str:
        if move is BlackjackMove.HIT:
            return "Hit"
        return "Stand"

    def resolve_round(
        self,
        game: BlackjackGame,
        player_move: BlackjackMove,
        opponent_move: BlackjackMove | None,
    ) -> RoundResult:
        detail: dict[str, object] = {
            "action": player_move.value,
            "player_total_before": game.player_total,
            "dealer_visible_total_before": PlayingCard.hand_total(game.visible_dealer_hand),
            "dealer_visible_hand_before": [card.short_name for card in game.visible_dealer_hand],
        }

        if player_move is BlackjackMove.HIT:
            drawn = self._draw_card(game)
            game.player_hand.append(drawn)
            detail["player_drew"] = drawn.short_name
            detail["player_total_after"] = game.player_total

            if game.player_total > 21:
                game.score["opponent"] = 1
                detail["outcome"] = "bust"
                game.round_detail = detail
                return RoundResult.LOSE

            if game.player_total < 21:
                detail["outcome"] = "continue"
                game.round_detail = detail
                return RoundResult.CONTINUE

        game.player_stood = True
        showdown_result = self._resolve_showdown(game, detail)
        game.round_detail = detail
        return showdown_result

    def build_round_notes(
        self,
        game: BlackjackGame,
        player_move: BlackjackMove,
        opponent_move: BlackjackMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["player_hand"] = [card.short_name for card in game.player_hand]
        detail["dealer_visible_hand"] = [card.short_name for card in game.visible_dealer_hand]
        if round_result != RoundResult.CONTINUE or game.reveal_policy == "full":
            detail["dealer_hand"] = [card.short_name for card in game.dealer_hand]
        return detail

    def get_journal_fragments(self, game: BlackjackGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        fragments: list[ContentFragment] = [
            ContentFragment(content=f"**Hand {last_round.round_number}**"),
        ]

        if notes.get("action") == BlackjackMove.HIT.value:
            fragments.append(
                ContentFragment(
                    content=f"You hit and draw {notes.get('player_drew', 'a card')}."
                )
            )
        elif notes.get("action") == BlackjackMove.STAND.value:
            fragments.append(
                ContentFragment(
                    content=f"You stand on {notes.get('player_total_before', game.player_total)}."
                )
            )

        fragments.append(
            ContentFragment(
                content=(
                    "Dealer shows "
                    + ", ".join(notes.get("dealer_visible_hand", []) or [])
                    + "."
                )
            )
        )

        if last_round.result == RoundResult.CONTINUE:
            fragments.append(
                ContentFragment(
                    content=f"Your total rises to {notes.get('player_total_after', game.player_total)}."
                )
            )
            return fragments

        if "dealer_draws" in notes:
            dealer_draws = ", ".join(notes["dealer_draws"])
            fragments.append(ContentFragment(content=f"Dealer draws {dealer_draws}."))

        if notes.get("dealer_hand"):
            dealer_hand = ", ".join(notes["dealer_hand"])
            fragments.append(ContentFragment(content=f"Dealer reveals {dealer_hand}."))

        outcome_line = {
            RoundResult.WIN: "The house blinks first. You take the hand.",
            RoundResult.LOSE: "The dealer closes it out before you can recover.",
            RoundResult.DRAW: "The hand settles into a draw.",
        }[last_round.result]
        fragments.append(ContentFragment(content=outcome_line))
        return fragments

    def _draw_card(self, game: BlackjackGame) -> PlayingCard:
        if not game.card_deck:
            raise RuntimeError("Blackjack deck exhausted")
        return game.card_deck.pop(0)

    def _stack_opening_deal(self, game: BlackjackGame) -> None:
        opening = self.OPENING_DEALS.get(game.deal_bias, [])
        if not opening:
            return

        remaining = list(game.card_deck)
        arranged: list[PlayingCard] = []
        for rank, suit in opening:
            idx = next(
                i
                for i, card in enumerate(remaining)
                if card.rank == rank and card.suit == suit
            )
            arranged.append(remaining.pop(idx))
        game.card_deck = arranged + remaining

    def _resolve_showdown(
        self,
        game: BlackjackGame,
        detail: dict[str, object],
    ) -> RoundResult:
        dealer_draws: list[str] = []
        while game.dealer_total < game.dealer_stand_at:
            drawn = self._draw_card(game)
            game.dealer_hand.append(drawn)
            dealer_draws.append(drawn.short_name)

        if dealer_draws:
            detail["dealer_draws"] = dealer_draws

        detail["player_total_after"] = game.player_total
        detail["dealer_total_after"] = game.dealer_total
        detail["dealer_hand"] = [card.short_name for card in game.dealer_hand]

        if game.dealer_total > 21 or game.player_total > game.dealer_total:
            game.score["player"] = 1
            detail["outcome"] = "player_win"
            return RoundResult.WIN

        if game.dealer_total > game.player_total:
            game.score["opponent"] = 1
            detail["outcome"] = "dealer_win"
            return RoundResult.LOSE

        game.score["player"] = 1
        game.score["opponent"] = 1
        detail["outcome"] = "push"
        return RoundResult.DRAW
