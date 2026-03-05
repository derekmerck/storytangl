from __future__ import annotations

"""VM phase handlers for game mechanics integration."""

import logging
from typing import TYPE_CHECKING, Any

from tangl.core38 import CallReceipt as CallReceipt38, Selector as Selector38
from tangl.mechanics.games import GamePhase, GameResult, RoundResult
from tangl.vm import (
    ResolutionPhase as P,
    is_first_visit,
    on_gather_ns,
    on_journal,
    on_prereqs,
    on_provision,
    on_update,
)
from tangl.vm.dispatch import vm_dispatch
from tangl.core import CallReceipt
from tangl.core.behavior import HandlerPriority as Prio
from tangl.story.dispatch import on_gather_content
from tangl.vm38.dispatch import dispatch as vm38_dispatch

from .has_game import HasGame

if TYPE_CHECKING:
    from tangl.vm import Context

logger = logging.getLogger(__name__)

# todo: should probably register these on story dispatch instead of vm


def _ctx_frame(ctx: Any) -> Any | None:
    """Return legacy frame from context when available."""
    return getattr(ctx, "_frame", None)


def _ctx_cursor_history(ctx: Any) -> list[Any] | None:
    """Resolve cursor-history-like data from legacy frame when present."""
    frame = _ctx_frame(ctx)
    history = getattr(frame, "cursor_history", None) if frame is not None else None
    return history if isinstance(history, list) else None


def _ctx_selected_payload(ctx: Any) -> Any:
    """Extract selected payload from vm38/legacy context + frame bridges."""
    payload = getattr(ctx, "selected_payload", None)
    if payload is not None:
        return payload

    payload = getattr(ctx, "incoming_payload", None)
    if payload is not None:
        return payload

    frame = _ctx_frame(ctx)
    if frame is not None:
        selected_edge = getattr(frame, "selected_edge", None)
        if selected_edge is not None:
            payload = getattr(selected_edge, "payload", None)
            if payload is not None:
                return payload

    selected_edge = getattr(ctx, "selected_edge", None)
    if selected_edge is not None:
        return getattr(selected_edge, "payload", None)

    incoming_edge = getattr(ctx, "incoming_edge", None)
    if incoming_edge is not None:
        return getattr(incoming_edge, "payload", None)

    return None


@vm_dispatch.register(task=P.PREREQS, caller=HasGame)
@on_prereqs(wants_caller_kind=HasGame, wants_exact_kind=False)
def setup_game_on_first_visit(
    cursor: HasGame | None = None,
    *,
    caller: HasGame | None = None,
    ctx: Context,
    **kwargs: Any,
):
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

    cursor = cursor if isinstance(cursor, HasGame) else caller
    if not isinstance(cursor, HasGame):
        return None

    cursor_history = _ctx_cursor_history(ctx)
    if cursor_history is not None:
        if not is_first_visit(cursor.uid, cursor_history):
            return None
    elif cursor.game.phase == GamePhase.READY:
        # vm38 contexts do not expose frame history directly; phase is enough
        # to prevent repeated setup in steady-state traversal.
        return None

    logger.debug("First visit to %s; initializing game", cursor.get_label())

    if cursor.game.phase != GamePhase.READY:
        cursor.game_handler.setup(cursor.game)
        cursor.locals["game_initialized"] = True

    return None


@vm_dispatch.register(task=P.PLANNING, caller=HasGame)
@on_provision(wants_caller_kind=HasGame, wants_exact_kind=False)
def provision_game_moves(
    cursor: HasGame | None = None,
    *,
    caller: HasGame | None = None,
    ctx: Context,
    **kwargs: Any,
):
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

    from tangl.story38 import Action

    cursor = cursor if isinstance(cursor, HasGame) else caller
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
    # vm38 PLANNING handlers are side-effect-only: returning non-None results
    # causes do_provision() to raise. Keep list-return behavior for direct calls
    # used by legacy-style tests/helpers.
    if getattr(ctx, "current_phase", None) == P.PLANNING and hasattr(ctx, "incoming_edge"):
        return None
    return actions


@vm_dispatch.register(task=P.UPDATE, caller=HasGame)
@on_update(wants_caller_kind=HasGame, wants_exact_kind=False)
def process_game_move(
    cursor: HasGame | None = None,
    *,
    caller: HasGame | None = None,
    ctx: Context,
    **kwargs: Any,
):
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

    cursor = cursor if isinstance(cursor, HasGame) else caller
    if not isinstance(cursor, HasGame):
        return None

    payload = _ctx_selected_payload(ctx)
    if not isinstance(payload, dict):
        logger.debug("No selected move payload at %s", cursor.get_label())
        return None

    move = payload.get("move")

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

    # Context namespaces cache values per cursor; refresh so POSTREQ predicates
    # read the updated game_* flags from :func:`inject_game_context`.
    frame = _ctx_frame(ctx)
    if frame is not None and hasattr(frame, "_invalidate_context"):
        frame._invalidate_context()
    # vm38 caches namespaces per follow-edge hop; clear after UPDATE so
    # POSTREQS sees fresh game_* flags in the same pipeline pass.
    ns_cache = getattr(ctx, "_ns_cache", None)
    if isinstance(ns_cache, dict):
        ns_cache.clear()
    ns_inflight = getattr(ctx, "_ns_inflight", None)
    if isinstance(ns_inflight, set):
        ns_inflight.clear()

    return None


@vm_dispatch.register(task=P.JOURNAL, caller=HasGame)
@on_journal(wants_caller_kind=HasGame, wants_exact_kind=False)
def generate_game_journal(
    cursor: HasGame | None = None,
    *,
    caller: HasGame | None = None,
    ctx: Context,
    **kwargs: Any,
):
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

    cursor = cursor if isinstance(cursor, HasGame) else caller
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
@on_gather_ns(wants_caller_kind=HasGame, wants_exact_kind=False)
def inject_game_context(
    cursor: HasGame | None = None,
    *,
    caller: HasGame | None = None,
    ctx: Context,
    **kwargs: Any,
) -> dict[str, Any]:
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

    cursor = cursor if isinstance(cursor, HasGame) else caller
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


@on_gather_content(caller=HasGame, priority=Prio.FIRST)
def game_gather_content(cursor: HasGame, *, ctx: Context, **kwargs: Any):
    """
    Generate game journal content via ``generate_journal`` subdispatch.

    Runs with FIRST priority so blocks embedding games prefer the game's
    generated journal content over inline block content. Returns either a
    string (for post-processing) or a list of fragments produced by
    ``generate_journal`` handlers.
    """

    if not isinstance(cursor, HasGame):
        return None

    game = getattr(cursor, "game", None)
    if game is None:
        return None

    fresh_call_receipts = getattr(ctx, "_fresh_call_receipts", None)
    if callable(fresh_call_receipts):
        with fresh_call_receipts():
            game_receipts = vm_dispatch.dispatch(
                caller=game,
                task="generate_journal",
                ctx=ctx,
            )
    else:
        game_receipts = vm_dispatch.dispatch(
            caller=game,
            task="generate_journal",
            ctx=ctx,
        )

    content = CallReceipt.first_result(*game_receipts)

    if content:
        return content

    # vm38 fallback: custom game journal handlers may register on the vm38
    # phase bus during migration away from legacy vm_dispatch tasks.
    vm38_receipts = list(
        vm38_dispatch.execute_all(
            task="generate_journal",
            call_kwargs={"caller": game},
            ctx=ctx,
            selector=Selector38(caller_kind=type(game)),
        )
    )
    vm38_content = CallReceipt38.first_result(*vm38_receipts)
    return vm38_content if vm38_content else None
