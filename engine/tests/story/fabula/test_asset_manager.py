from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core.graph import Graph, Token
from tangl.story.concepts.asset import AssetType
from tangl.story.fabula import AssetManager


class Deck(AssetType):
    card_count: int = 52
    shuffle_state: list[int] = Field(default_factory=list, json_schema_extra={"instance_var": True})


@pytest.fixture(autouse=True)
def _clear_deck_instances() -> None:
    yield
    Deck.clear_instances()


def test_create_token_from_registered_asset() -> None:
    manager = AssetManager()
    manager.register_discrete_class("decks", Deck)
    Deck(label="standard", card_count=52)

    graph = Graph(label="test")
    token = manager.create_token("decks", "standard", graph)

    assert isinstance(token, Token)
    assert token.label == "standard"
    assert token.card_count == 52
    assert token in graph


def test_create_token_allows_overlay() -> None:
    manager = AssetManager()
    manager.register_discrete_class("decks", Deck)
    Deck(label="standard", card_count=52)

    graph = Graph(label="test")
    token = manager.create_token(
        "decks",
        "standard",
        graph,
        overlay={"shuffle_state": [1, 2, 3]},
    )

    assert token.shuffle_state == [1, 2, 3]


def test_create_token_requires_registered_type() -> None:
    manager = AssetManager()

    with pytest.raises(ValueError, match="not registered"):
        manager.create_token("unknown", "missing")


def test_create_token_errors_when_base_missing() -> None:
    manager = AssetManager()
    manager.register_discrete_class("decks", Deck)

    with pytest.raises(ValueError, match="Available"):
        manager.create_token("decks", "missing")
