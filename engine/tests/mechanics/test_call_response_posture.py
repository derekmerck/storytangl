"""A call-response contest poses its staged opponent from game state.

The posture is state, not a timeline: an opponent holding the initiative is
attacking (``call``); one waiting on the player's line is on guard (``response``).
The claims under test are that the pose follows initiative, that an author's
explicit clip wins, and that an ambiguous stage is left alone rather than guessed.
"""

from __future__ import annotations

from types import SimpleNamespace

from tangl.journal.fragments import ContentFragment, MediaFragment
from tangl.mechanics.games import CallResponseGame
from tangl.mechanics.games.call_response_presentation import posture_clip, stage_call_response_posture
from tangl.presentation.hints import StagingHints


def _portrait(role: str = "dialog_im", **hints) -> MediaFragment:
    return MediaFragment(
        content="opponent.png", content_format="url", media_role=role,
        staging_hints=StagingHints(**hints) if hints else None,
    )


def _contest(*, player_has_initiative: bool) -> SimpleNamespace:
    return SimpleNamespace(game=CallResponseGame(player_has_initiative=player_has_initiative))


def _clips(fragments) -> list[str | None]:
    return [getattr(f.staging_hints, "media_clip", None) for f in fragments if isinstance(f, MediaFragment)]


def test_an_opponent_holding_the_initiative_is_attacking() -> None:
    assert posture_clip(CallResponseGame(player_has_initiative=False)) == "call"


def test_an_opponent_waiting_on_the_player_is_on_guard() -> None:
    assert posture_clip(CallResponseGame(player_has_initiative=True)) == "response"


def test_the_staged_opponent_takes_the_pose_and_the_scenery_does_not() -> None:
    fragments = [
        MediaFragment(content="yard.png", content_format="url", media_role="narrative_im"),
        ContentFragment(content="The dockhand squares up."),
        _portrait(),
    ]

    composed = stage_call_response_posture(caller=_contest(player_has_initiative=False), fragments=fragments)

    assert _clips(composed) == [None, "call"]
    assert composed[1] is fragments[1]


def test_other_staging_on_the_opponent_is_kept() -> None:
    composed = stage_call_response_posture(
        caller=_contest(player_has_initiative=True),
        fragments=[_portrait(media_x="right", media_flip_h=True, media_timing="loop")],
    )

    hints = composed[0].staging_hints
    assert (hints.media_x, hints.media_flip_h, hints.media_timing, hints.media_clip) == ("right", True, "loop", "response")


def test_a_clip_the_script_already_names_wins() -> None:
    fragments = [_portrait(media_clip="idle")]

    assert stage_call_response_posture(caller=_contest(player_has_initiative=False), fragments=fragments) is None


def test_two_portraits_are_left_alone_rather_than_guessed_between() -> None:
    """With no data saying which is the opponent, a wrong pose is worse than none."""

    fragments = [_portrait(), _portrait(role="avatar_im")]

    assert stage_call_response_posture(caller=_contest(player_has_initiative=False), fragments=fragments) is None


def test_a_block_whose_game_is_not_call_response_is_untouched() -> None:
    caller = SimpleNamespace(game=object())

    assert stage_call_response_posture(caller=caller, fragments=[_portrait()]) is None


def test_the_input_batch_is_not_mutated() -> None:
    """compose_journal folds: the next handler must see this one's output, not a shared list."""

    fragments = [_portrait()]
    stage_call_response_posture(caller=_contest(player_has_initiative=False), fragments=fragments)

    assert fragments[0].staging_hints is None
