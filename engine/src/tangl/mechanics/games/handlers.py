from __future__ import annotations

"""VM phase handlers for game mechanics integration."""

import logging
from typing import TYPE_CHECKING, Any

from tangl.mechanics.games import GamePhase, GameResult, RoundResult
from tangl.vm import (
    ResolutionPhase as P,
    on_gather_ns,
    on_journal,
    on_provision,
    on_update,
)

from .has_game import HasGame

if TYPE_CHECKING:
    from tangl.vm import VmPhaseCtx as Context

logger = logging.getLogger(__name__)

def _has_tags(value: Any, *tags: str) -> bool:
    actual = getattr(value, "tags", set()) or set()
    return set(tags).issubset(actual)


def _clear_dynamic_game_actions(cursor: HasGame, *, ctx: Context) -> None:
    from tangl.core import Selector
    from tangl.story import Action

    graph = cursor.graph

    for edge in list(cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))):
        if _has_tags(edge, "dynamic", "fanout", "game"):
            graph.remove(edge.uid, _ctx=ctx)


def _build_game_actions(cursor: HasGame) -> list[Any]:
    from tangl.story import Action

    actions: list[Action] = []
    for move in cursor.game_handler.get_provisioned_moves(cursor.game):
        actions.append(
            Action(
                graph=cursor.graph,
                predecessor_id=cursor.uid,
                successor_id=cursor.uid,
                label=cursor.game_handler.get_move_label(cursor.game, move),
                payload={"move": move},
                accepts=cursor.game_handler.get_move_accepts(cursor.game, move),
                tags={"dynamic", "fanout", "game"},
                # Minimal cleanup-attribution token (synthesis item D): names the
                # projecting family in the same channel sandbox already uses, so
                # game moves are as cleanup-explainable as sandbox interactions.
                # "game_self_loop" (not "game_fanout") to avoid echoing the
                # recorded fanout-tag drift; lifecycle/diagnostic only, tags
                # remain the cleanup authority.
                ui_hints={"source": "game_self_loop"},
            )
        )
    return actions


def _ctx_selected_payload(ctx: Context) -> Any:
    """Return the selected edge payload for the current VM turn."""

    return ctx.selected_payload


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

    When the game is READY, the handler queries client-facing provisioned moves
    from the game handler and returns one
    :class:`~tangl.story.episode.action.Action` per move. Each action is a
    self-loop with the move stored in ``payload`` for later processing during
    :data:`~tangl.vm.resolution_phase.ResolutionPhase.UPDATE`.

    Returns
    -------
    list[Action]
        One action per provisioned move, or an empty list when the game is not
        accepting player input.
    """

    from tangl.story import Action

    cursor = cursor if isinstance(cursor, HasGame) else caller
    if not isinstance(cursor, HasGame):
        return []

    if cursor.game_handler.dynamic_move_projection:
        _clear_dynamic_game_actions(cursor, ctx=ctx)

    if cursor.game.phase != GamePhase.READY:
        if (
            cursor.game.phase is GamePhase.PENDING
            and ctx.current_phase is P.PLANNING
        ):
            # Planning may prove and materialize the next challenge frontier
            # (for example, credential packet presentation) without accepting
            # or initializing its embedded game state.
            cursor.game_handler.provision_presentation(cursor.game, ctx=ctx)
        logger.debug("Game not ready at %s; skipping move provisioning", cursor.get_label())
        return None if ctx.current_phase is P.PLANNING else []

    if ctx.current_phase is P.PLANNING:
        cursor.game_handler.provision_presentation(cursor.game, ctx=ctx)

    if not cursor.game_handler.dynamic_move_projection:
        return None if ctx.current_phase is P.PLANNING else []

    moves = cursor.game_handler.get_provisioned_moves(cursor.game)

    if not moves:
        logger.warning("No available moves at %s despite READY phase", cursor.get_label())
        return None if ctx.current_phase is P.PLANNING else []

    actions = _build_game_actions(cursor)

    logger.debug("Provisioned %s move actions at %s", len(actions), cursor.get_label())
    # VM PLANNING handlers are side-effect-only: returning non-None results
    # causes do_provision() to raise. Keep list-return behavior for direct calls
    # used by tests and helper utilities outside the live frame pipeline.
    if ctx.current_phase is P.PLANNING:
        return None
    return actions


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

    Extracts ``move`` from the selected action payload, resolves any submitted
    widget data through the game handler, then forwards the concrete move to
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

    if cursor.game.phase is GamePhase.PENDING:
        cursor.prepare_game(ctx=ctx)
        cursor.game_handler.setup(cursor.game)
        ctx.invalidate_namespaces()
        if cursor.game_handler.dynamic_move_projection:
            _clear_dynamic_game_actions(cursor, ctx=ctx)
            _build_game_actions(cursor)

    payload = _ctx_selected_payload(ctx)
    if not isinstance(payload, dict):
        logger.debug("No selected move payload at %s", cursor.get_label())
        return None

    move = payload.get("move")

    if move is None:
        logger.warning("Selected edge missing move payload at %s", cursor.get_label())
        return None
    move = cursor.game_handler.resolve_move_payload(cursor.game, move, payload)

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

    ctx.invalidate_namespaces()

    if cursor.game_handler.dynamic_move_projection:
        _clear_dynamic_game_actions(cursor, ctx=ctx)
    if (
        cursor.game_handler.dynamic_move_projection
        and cursor.game.phase is GamePhase.READY
        and not cursor.game.result.is_terminal
    ):
        actions = _build_game_actions(cursor)
        logger.debug(
            "Refreshed %s game actions after update at %s",
            len(actions),
            cursor.get_label(),
        )
    elif cursor.game.phase is GamePhase.TERMINAL:
        cursor.project_game_outcomes(ctx=ctx)

    return None


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

    from tangl.journal.fragments import ContentFragment

    cursor = cursor if isinstance(cursor, HasGame) else caller
    if not isinstance(cursor, HasGame):
        return []

    custom_fragments = cursor.game_handler.get_journal_fragments(cursor.game, ctx=ctx)
    if custom_fragments is not None:
        logger.debug(
            "Generated %s tailored journal fragments for %s",
            len(custom_fragments),
            cursor.get_label(),
        )
        return custom_fragments

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

    namespace = cursor.game.to_namespace()
    namespace.update(
        {
            "game_phase": cursor.game.phase.value,
            "game_round": cursor.game.round,
            "game_won": cursor.game.result == GameResult.WIN,
            "game_lost": cursor.game.result == GameResult.LOSE,
            "game_draw": cursor.game.result == GameResult.DRAW,
            "game_in_progress": cursor.game.result == GameResult.IN_PROCESS,
        }
    )
    return namespace
