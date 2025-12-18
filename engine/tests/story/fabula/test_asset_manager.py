from __future__ import annotations

import pytest

from tangl.core.graph import Node
from tangl.story.fabula import AssetManager, DomainManager
from tangl.story.story_graph import StoryGraph


def test_asset_manager_register_and_has_asset():
    manager = AssetManager()

    manager.register(
        asset_ref="test_asset",
        template={"obj_cls": "tangl.core.graph.Node", "label": "test_item"},
    )

    assert manager.has_asset("test_asset")
    assert "test_asset" in manager.list_assets()


def test_create_token_from_registered_asset():
    manager = AssetManager()
    graph = StoryGraph(label="test")

    manager.register(
        asset_ref="standard_deck",
        template={
            "obj_cls": "tangl.core.graph.Node",
            "label": "standard_deck",
            "name": "Standard Deck of Cards",
            "card_count": 52,
        },
    )

    token = manager.create_token(asset_ref="standard_deck", graph=graph)

    assert isinstance(token, Node)
    assert token.label == "standard_deck"
    assert token.name == "Standard Deck of Cards"
    assert token in graph


def test_create_token_overlays_do_not_mutate_template():
    manager = AssetManager()
    graph = StoryGraph(label="test")

    manager.register(
        asset_ref="deck",
        template={"obj_cls": "tangl.core.graph.Node", "label": "deck", "card_count": 52},
    )

    first = manager.create_token(asset_ref="deck", graph=graph, shuffle_state=[1, 2, 3])
    second = manager.create_token(asset_ref="deck", graph=graph, shuffle_state=[3, 2, 1])

    assert first is not second
    assert first.shuffle_state == [1, 2, 3]
    assert second.shuffle_state == [3, 2, 1]

    stored_template = manager._asset_templates["deck"]
    assert "shuffle_state" not in stored_template


def test_create_token_uses_domain_manager_resolution():
    manager = AssetManager()
    graph = StoryGraph(label="test")
    domain_manager = DomainManager()

    manager.register(
        asset_ref="custom_node",
        template={"obj_cls": "tangl.core.graph.Node", "label": "custom_node"},
    )

    token = manager.create_token(
        asset_ref="custom_node",
        graph=graph,
        domain_manager=domain_manager,
    )

    assert isinstance(token, Node)
    assert token.label == "custom_node"


def test_create_token_errors_when_asset_missing():
    manager = AssetManager()
    graph = StoryGraph(label="test")

    with pytest.raises(ValueError, match="missing"):
        manager.create_token(asset_ref="missing", graph=graph)

