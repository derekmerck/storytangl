from __future__ import annotations

"""VM phase handlers for game mechanics integration."""

import logging
from typing import TYPE_CHECKING, Any

from tangl.mechanics.games import GamePhase, GameResult, RoundResult
from tangl.vm import is_first_visit
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.resolution_phase import ResolutionPhase as P

from .has_game import HasGame

if TYPE_CHECKING:
    from tangl.vm import Context

logger = logging.getLogger(__name__)


@vm_dispatch.register(task=P.PREREQS, caller=HasGame)
def setup_game_on_first_visit(cursor: HasGame, *, ctx: Context, **kwargs: Any):
    """
    Initialize the embedded game when the block is first visited.

    Runs during :data:`~tangl.vm.resolution_phase.ResolutionPhase.PREREQS` to
    ensure the game is ready before move provisioning. Uses the shared cursor
    history to detect first entry and calls ``setup`` on the handler when the
    game has not yet transitioned to READY.

    Returns
    -------
    None
        This handler never redirects traversal.
    """

    if not isinstance(cursor, HasGame):
        return None

    frame = ctx._frame

    if not is_first_visit(cursor.uid, frame.cursor_history):
        return None

    logger.debug("First visit to %s; initializing game", cursor.get_label())

    if cursor.game.phase != GamePhase.READY:
        cursor.game_handler.setup(cursor.game)
        cursor.locals["game_initialized"] = True

    return None


@vm_dispatch.register(task=P.PLANNING, caller=HasGame)
def provision_game_moves(cursor: HasGame, *, ctx: Context, **kwargs: Any):
    """
    Provision self-loop :class:`~tangl.story.episode.action.Action` choices for moves.

    When the game is READY, the handler queries available moves from the
    game handler and returns one :class:`~tangl.story.episode.action.Action`
    per move. Each action is a self-loop with the move stored in ``payload``
    for later processing during :data:`~tangl.vm.resolution_phase.ResolutionPhase.UPDATE`.

    Returns
    -------
    list[Action]
        One action per available move, or an empty list when the game is not
        accepting player input.
    """

    from tangl.story.episode.action import Action

    if not isinstance(cursor, HasGame):
        return []

    if cursor.game.phase != GamePhase.READY:
        logger.debug("Game not ready at %s; skipping move provisioning", cursor.get_label())
        return []

    moves = cursor.game_handler.get_available_moves(cursor.game)

    if not moves:
        logger.warning("No available moves at %s despite READY phase", cursor.get_label())
        return []

    actions: list[Action] = []
    for move in moves:
        actions.append(
            Action(
                graph=cursor.graph,
                source_id=cursor.uid,
                destination_id=cursor.uid,
                label=f"Play {move}",
                payload={"move": move},
            )
        )

    logger.debug("Provisioned %s move actions at %s", len(actions), cursor.get_label())
    return actions


@vm_dispatch.register(task=P.UPDATE, caller=HasGame)
def process_game_move(cursor: HasGame, *, ctx: Context, **kwargs: Any):
    """
    Apply the player's selected move through the game handler.

    Extracts ``move`` from the selected action payload, forwards it to
    :meth:`~tangl.mechanics.games.handler.GameHandler.receive_move`, and
    records round/game outcomes in ``cursor.locals`` for downstream JOURNAL
    and CONTEXT phases.

    Returns
    -------
    None
        Updates occur in-place on ``cursor.game``; no redirect is produced.
    """

    if not isinstance(cursor, HasGame):
        return None

    frame = ctx._frame
    selected_edge = getattr(frame, "selected_edge", None)

    if selected_edge is None or not getattr(selected_edge, "payload", None):
        logger.debug("No selected move payload at %s", cursor.get_label())
        return None

    move = selected_edge.payload.get("move")

    if move is None:
        logger.warning("Selected edge missing move payload at %s", cursor.get_label())
        return None

    if cursor.game.phase != GamePhase.READY:
        logger.warning(
            "Cannot process move in phase %s at %s", cursor.game.phase, cursor.get_label()
        )
        return None

    round_result = cursor.game_handler.receive_move(cursor.game, move)

    if cursor.game.history:
        cursor.locals["last_round"] = cursor.game.history[-1]

    cursor.locals["game_result"] = cursor.game.result
    cursor.locals["round_result"] = round_result

    logger.debug(
        "Processed move %s at %s → result=%s round=%s",
        move,
        cursor.get_label(),
        cursor.game.result,
        cursor.game.round,
    )

    return None


@vm_dispatch.register(task=P.JOURNAL, caller=HasGame)
def generate_game_journal(cursor: HasGame, *, ctx: Context, **kwargs: Any):
    """
    Build journal fragments summarizing the last round.

    Reads ``cursor.locals['last_round']`` (stored during UPDATE) and emits
    :class:`~tangl.journal.content.ContentFragment` instances describing the
    player's move, opponent move (when available), round outcome, and current
    score if tracked.

    Returns
    -------
    list[ContentFragment]
        Narrative fragments for the most recent round, or an empty list when no
        round has been recorded in this step.
    """

    from tangl.journal.content import ContentFragment

    if not isinstance(cursor, HasGame):
        return []

    last_round = cursor.locals.get("last_round")
    if not last_round:
        logger.debug("No last_round available for journal at %s", cursor.get_label())
        return []

    fragments: list[ContentFragment] = []

    fragments.append(
        ContentFragment(content=f"You played {last_round.player_move}.")
    )

    if last_round.opponent_move is not None:
        fragments.append(
            ContentFragment(content=f"Opponent played {last_round.opponent_move}.")
        )

    if last_round.result == RoundResult.WIN:
        fragments.append(ContentFragment(content="You won this round."))
    elif last_round.result == RoundResult.LOSE:
        fragments.append(ContentFragment(content="You lost this round."))
    elif last_round.result == RoundResult.DRAW:
        fragments.append(ContentFragment(content="It's a draw."))

    if hasattr(cursor.game, "score") and cursor.game.score:
        player_score = cursor.game.score.get("player", 0)
        opponent_score = cursor.game.score.get("opponent", 0)
        fragments.append(ContentFragment(content=f"Score: {player_score}-{opponent_score}"))

    logger.debug("Generated %s journal fragments for %s", len(fragments), cursor.get_label())
    return fragments


@vm_dispatch.register(task="get_ns", caller=HasGame)
def inject_game_context(cursor: HasGame, *, ctx: Context, **kwargs: Any) -> dict[str, Any]:
    """
    Expose game state to the VM predicate namespace.

    Injects phase/result metadata used by POSTREQS exit predicates and for
    debugging during traversal. Registered against the ``get_ns`` dispatch
    task so the values participate in namespace composition alongside locals
    and dependency affordances.

    Returns
    -------
    dict[str, Any]
        Namespace entries prefixed with ``game_`` for predicate access.
    """

    if not isinstance(cursor, HasGame):
        return {}

    return {
        "game_phase": cursor.game.phase.value,
        "game_round": cursor.game.round,
        "game_won": cursor.game.result == GameResult.WIN,
        "game_lost": cursor.game.result == GameResult.LOSE,
        "game_draw": cursor.game.result == GameResult.DRAW,
        "game_in_progress": cursor.game.result == GameResult.IN_PROCESS,
    }
