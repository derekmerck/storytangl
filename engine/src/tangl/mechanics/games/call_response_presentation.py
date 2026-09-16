"""Stage a call-response opponent in the posture its game state implies.

A contest block stages its opponent's portrait like any block stages media. This
adds one per-use hint to that portrait each turn: which clip of its sprite sheet
shows the opponent's current posture.

The posture is state, not a timeline:

- the opponent holds the initiative -- its call is chosen and the player must
  answer -- so it is mid-attack: ``call``;
- the player holds the initiative, so the opponent is on guard waiting for the
  player's line: ``response``.

No outcome is shown here, and nothing is sequenced. A lunge followed by a parry
inside one turn would be a cinematic timeline, which this contract deliberately
does not have; an aftermath block that wants to show who won says so in its own
script.

The clip names are the kernel's own :data:`PhraseRole` vocabulary, not art
vocabulary, which is what lets interchangeable art packs keep supplying the same
names. A client without sprite sheets ignores the hint and draws the still.

It registers on ``presentation_dispatch``, not the VM's registry. The VM runs the
``compose_journal`` fold; this contribution is presentation syntax a generic
mechanic adds to it, and owning a hook in the lifecycle is not its business.
"""

from __future__ import annotations

from typing import Any

from tangl.journal.fragments import MediaFragment
from tangl.presentation.dispatch import on_compose_journal
from tangl.presentation.hints import StagingHints

from .call_response_game import CallResponseGame
from .has_game import HasGame

PORTRAIT_ROLES = frozenset({"dialog_im", "avatar_im"})


def posture_clip(game: CallResponseGame) -> str:
    """The opponent's current posture, named with the kernel's phrase roles."""

    return "response" if game.player_has_initiative else "call"


@on_compose_journal(wants_caller_kind=HasGame, wants_exact_kind=False)
def stage_call_response_posture(*, caller: HasGame, fragments: list[Any], **_kw: Any) -> list[Any] | None:
    """Set ``media_clip`` on the contest's staged opponent, unless the script already has.

    Exactly one portrait, or none of them. With two portraits on stage there is no
    data saying which is the opponent, and a guessed pose on the wrong character is
    worse than no pose: the stills still render. A script that names a clip wins,
    because an author who asked for one meant it.
    """

    # ``caller.game`` would *create* the game on first read and store it in the
    # block's persisted ``game_state``. Composing a journal is a read, so it asks
    # for the state that exists: no game yet means no posture, and the still draws.
    game = caller.game_state
    if not isinstance(game, CallResponseGame):
        return None

    portraits = [
        index
        for index, fragment in enumerate(fragments)
        if isinstance(fragment, MediaFragment) and fragment.media_role in PORTRAIT_ROLES
    ]
    if len(portraits) != 1:
        return None
    fragment = fragments[portraits[0]]
    hints = fragment.staging_hints or StagingHints()
    if hints.media_clip is not None:
        return None

    staged = fragment.model_copy(update={"staging_hints": hints.model_copy(update={"media_clip": posture_clip(game)})})
    composed = list(fragments)
    composed[portraits[0]] = staged
    return composed


__all__ = ["PORTRAIT_ROLES", "posture_clip", "stage_call_response_posture"]
