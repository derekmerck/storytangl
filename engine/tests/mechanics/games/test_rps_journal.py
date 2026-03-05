"""Journal generation tests for RPS and RPSLS."""

from __future__ import annotations

from tangl.mechanics.games.rps_game import (
    RpsGame,
    RpsGameHandler,
    RpsMove,
    RpslsGame,
    RpslsGameHandler,
    RpslsMove,
    rps_generate_journal,
    rpsls_generate_journal,
)


def test_rps_journal_has_thematic_verbs() -> None:
    """RPS journal uses thematic verbs (crushes/cuts/covers)."""

    game = RpsGame(scoring_n=2)
    handler = RpsGameHandler()
    handler.setup(game)
    game.opponent_next_move = RpsMove.SCISSORS
    handler.receive_move(game, RpsMove.ROCK)

    fragments = rps_generate_journal(caller=game, ctx=None) or []
    content = " ".join(fragment.content for fragment in fragments if hasattr(fragment, "content"))
    assert "crushes" in content.lower()


def test_rps_journal_shows_score_and_round() -> None:
    """RPS journal includes round header and score."""

    game = RpsGame(scoring_n=3)
    handler = RpsGameHandler()
    handler.setup(game)
    game.opponent_next_move = RpsMove.SCISSORS
    handler.receive_move(game, RpsMove.ROCK)

    fragments = rps_generate_journal(caller=game, ctx=None) or []
    content = " ".join(fragment.content for fragment in fragments if hasattr(fragment, "content"))
    assert "round 1" in content.lower()
    assert "score:" in content.lower()
    assert "1-0" in content


def test_rpsls_journal_uses_extended_verbs() -> None:
    """RPSLS narrative uses the extended verb templates."""

    game = RpslsGame(scoring_n=3)
    handler = RpslsGameHandler()
    handler.setup(game)
    game.opponent_next_move = RpslsMove.ROCK
    handler.receive_move(game, RpslsMove.SPOCK)

    fragments = rpsls_generate_journal(caller=game, ctx=None) or []
    content = " ".join(fragment.content for fragment in fragments if hasattr(fragment, "content"))
    assert "vaporizes" in content.lower() or "smashes" in content.lower()
