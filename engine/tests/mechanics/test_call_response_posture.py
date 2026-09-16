"""A call-response contest poses its staged opponent from game state.

The posture is state, not a timeline: an opponent holding the initiative is
attacking (``call``); one waiting on the player's line is on guard (``response``).
The claims under test are that the pose follows initiative, that an author's
explicit clip wins, that an ambiguous stage is left alone rather than guessed, and
that the contribution is presentation syntax: it registers with presentation, not
with the VM that drives the fold.
"""

from __future__ import annotations

from tangl.core import Graph
from tangl.journal.fragments import ContentFragment, MediaFragment
from tangl.mechanics.games import CallResponseGame, Game, HasGame
from tangl.mechanics.games.call_response_presentation import posture_clip, stage_call_response_posture
from tangl.presentation.hints import StagingHints
from tangl.story import Block


class Contest(HasGame, Block):
    """A real game block, because the handler reads a block's own state field."""

    _game_class = CallResponseGame


def _portrait(role: str = "dialog_im", **hints) -> MediaFragment:
    return MediaFragment(
        content="opponent.png", content_format="url", media_role=role,
        staging_hints=StagingHints(**hints) if hints else None,
    )


def _block(game: Game | None) -> Contest:
    block = Graph().add_node(kind=Contest, label="contest")
    block.game_state = game
    return block


def _contest(*, player_has_initiative: bool) -> Contest:
    return _block(CallResponseGame(player_has_initiative=player_has_initiative))


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
    assert stage_call_response_posture(caller=_block(Game()), fragments=[_portrait()]) is None


def test_the_input_batch_is_not_mutated() -> None:
    """compose_journal folds: the next handler must see this one's output, not a shared list."""

    fragments = [_portrait()]
    stage_call_response_posture(caller=_contest(player_has_initiative=False), fragments=fragments)

    assert fragments[0].staging_hints is None


def test_composing_a_journal_does_not_bring_a_game_into_being() -> None:
    """A block's ``game`` property creates and stores one; composing is a read.

    Reading it here would write a game into the block's persisted ``game_state``
    just by rendering a turn, for every ``HasGame`` block on stage.
    """

    block = Graph().add_node(kind=Contest, label="contest")
    assert block.game_state is None

    assert stage_call_response_posture(caller=block, fragments=[_portrait()]) is None
    assert block.game_state is None


def test_the_pose_is_contributed_to_presentation_not_to_the_vm() -> None:
    """The VM runs ``compose_journal``; staging a clip does not make a mechanic part of it."""

    from tangl.presentation.dispatch import presentation_dispatch
    from tangl.vm.dispatch import dispatch as vm_dispatch

    def composers(registry) -> list:
        return [b.func for b in registry.values() if b.task == "compose_journal"]

    assert stage_call_response_posture in composers(presentation_dispatch)
    assert stage_call_response_posture not in composers(vm_dispatch)
