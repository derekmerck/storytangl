"""Rock–Paper–Scissors tavern demo world."""
from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import RpsGame, RpsGameHandler
from tangl.story.mechanics.games import HasGame
from tangl.story.structure import Block


class RpsBlock(HasGame, Block):
    """Story block with a Rock–Paper–Scissors game facet."""


def load_world() -> Graph:
    """Build and return the RPS tavern graph."""
    graph = Graph(label="rps_tavern")

    entrance = graph.add_node(Block, label="entrance")
    victory = graph.add_node(Block, label="victory")
    defeat = graph.add_node(Block, label="defeat")

    challenge = RpsBlock.create_game_block(
        graph=graph,
        game_class=RpsGame,
        handler_class=RpsGameHandler,
        victory_dest=victory,
        defeat_dest=defeat,
        label="challenge",
    )

    challenge.game.scoring_strategy = "first_to_n"
    challenge.game.scoring_n = 2

    graph.add_edge(
        source=entrance,
        destination=challenge,
        label="Challenge the bartender",
    )

    return graph
