"""Journal generation tests for RPS and RPSLS."""

from __future__ import annotations

from tangl.mechanics.games.rps_game import (
    RpsGame,
    RpsGameHandler,
    RpsMove,
    RpslsGame,
    RpslsGameHandler,
    RpslsMove,
)
from tangl.story.episode import Block
from tangl.story.mechanics.games import HasGame
from tangl.story.story_graph import StoryGraph
from tangl.vm import Frame, ResolutionPhase as P


class RpsBlock(Block, HasGame):
    """Block mixin for RPS-family games."""


def _attach_game(block: Block, game: RpsGame | RpslsGame) -> None:
    object.__setattr__(block, "_game", game)


def test_rps_journal_has_thematic_verbs() -> None:
    """RPS journal uses thematic verbs (crushes/cuts/covers)."""

    graph = StoryGraph(label="test")
    game = RpsGame(scoring_n=2)
    handler = RpsGameHandler()
    handler.setup(game)
    game.opponent_next_move = RpsMove.SCISSORS
    handler.receive_move(game, RpsMove.ROCK)

    block = RpsBlock(graph=graph, label="game")
    _attach_game(block, game)

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    content = " ".join(fragment.content for fragment in fragments if hasattr(fragment, "content"))
    assert "crushes" in content.lower()


def test_rps_journal_shows_score_and_round() -> None:
    """RPS journal includes round header and score."""

    graph = StoryGraph(label="test")
    game = RpsGame(scoring_n=3)
    handler = RpsGameHandler()
    handler.setup(game)
    game.opponent_next_move = RpsMove.SCISSORS
    handler.receive_move(game, RpsMove.ROCK)

    block = RpsBlock(graph=graph, label="game")
    _attach_game(block, game)

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    content = " ".join(fragment.content for fragment in fragments if hasattr(fragment, "content"))
    assert "round 1" in content.lower()
    assert "score:" in content.lower()
    assert "1-0" in content


def test_rpsls_journal_uses_extended_verbs() -> None:
    """RPSLS narrative uses the extended verb templates."""

    graph = StoryGraph(label="test")
    game = RpslsGame(scoring_n=3)
    handler = RpslsGameHandler()
    handler.setup(game)
    game.opponent_next_move = RpslsMove.ROCK
    handler.receive_move(game, RpslsMove.SPOCK)

    block = RpsBlock(graph=graph, label="game")
    _attach_game(block, game)

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    content = " ".join(fragment.content for fragment in fragments if hasattr(fragment, "content"))
    assert "vaporizes" in content.lower() or "smashes" in content.lower()

