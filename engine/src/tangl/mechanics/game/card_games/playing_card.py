from __future__ import annotations
from typing import Iterable, Self, Literal
import random
import itertools

HasMedia = object

suits = ["s", "d", "c", "h"]
Suit = Literal[*suits]

class PlayingCard(HasMedia):

    def __init__(self, value: int, suit: Suit):
        if value < 1 or value > 13:
            raise ValueError("Card value must be between 1 and 13")
        if suit not in suits:
            raise ValueError(f"Invalid suit: {suit}")
        self.value = value
        self.suit = suit

    @classmethod
    def fresh_deck(cls):
        cards = [cls(v, s) for v, s in itertools.product(range(1, 14), suits)]
        random.shuffle(cards)
        return cards

    @classmethod
    def sum(cls, cards: Iterable[Self]) -> int:
        """Blackjack-style sum, 1 ace may be counted as 11"""
        _sum = 0
        num_aces = 0
        for card in cards:
            if card.value == 1:
                num_aces += 1
            _sum += min(card.value, 10)
        if _sum <= 11 and num_aces > 0:
            # at most 1 ace can be promoted
            _sum += 10
        return _sum

    def __str__(self):
        return f"{self.value}{self.suit.upper()}"

    def __repr__(self):
        return f"PlayingCard('{self!s}')"
