import pytest

from tangl.mechanics.games.card_games.playing_card import PlayingCard, suits

def test_card_creation():
    card = PlayingCard(1, 's')
    assert card.value == 1
    assert card.suit == 's'
    with pytest.raises(ValueError):
        PlayingCard(0, 's')
    with pytest.raises(ValueError):
        PlayingCard(14, 's')
    with pytest.raises(ValueError):
        PlayingCard(1, 'x')

def test_card_str():
    card = PlayingCard(1, 's')
    assert str(card) == "1S"
    card = PlayingCard(13, 'h')
    assert str(card) == "13H"

def test_fresh_deck():
    deck = PlayingCard.fresh_deck()
    assert len(deck) == 52
    values = set(card.value for card in deck)
    suits = set(card.suit for card in deck)
    assert values == set(range(1, 14))
    assert suits == {'s', 'd', 'c', 'h'}

def test_sum():
    cards = [PlayingCard(1, 's'), PlayingCard(10, 'h')]
    assert PlayingCard.sum(cards) == 21
    cards = [PlayingCard(1, 's'), PlayingCard(1, 'd')]
    assert PlayingCard.sum(cards) == 12
    cards = [PlayingCard(5, 's'), PlayingCard(5, 'h')]
    assert PlayingCard.sum(cards) == 10
    cards = [PlayingCard(13, 's'), PlayingCard(12, 'h')]
    assert PlayingCard.sum(cards) == 20

if __name__ == "__main__":
    pytest.main()
