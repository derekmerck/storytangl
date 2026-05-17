"""Optional sandbox adapter for incremental resource-allocation games."""

from __future__ import annotations

from uuid import UUID

from tangl.core import Priority, Selector
from tangl.journal.fragments import ContentFragment
from tangl.mechanics.games import (
    GamePhase,
    HasGame,
    IncrementalGame,
    IncrementalGameHandler,
    IncrementalMove,
)
from tangl.story import Action
from tangl.vm import VmPhaseCtx, on_journal, on_provision, on_update

from .dispatch import on_sandbox_tick
from .handlers import sandbox_scopes
from .location import SandboxLocation
from .time import SandboxTickEvent, SandboxTimeCost


def _has_tags(value, *tags: str) -> bool:
    actual = value.tags or set()
    return set(tags).issubset(actual)


def _hosted_incremental_games(location: SandboxLocation) -> list[HasGame]:
    games: list[HasGame] = []
    for scope in sandbox_scopes(location):
        for child in scope.children():
            if not isinstance(child, HasGame):
                continue
            if not isinstance(child.game, IncrementalGame):
                continue
            if not isinstance(child.game_handler, IncrementalGameHandler):
                continue
            games.append(child)
    return games


def _ensure_incremental_ready(host: HasGame) -> None:
    if host.game.phase == GamePhase.PENDING:
        host.game_handler.setup(host.game)
        host.locals["game_initialized"] = True


def _clear_incremental_actions(location: SandboxLocation, *, ctx: VmPhaseCtx) -> None:
    graph = location.graph
    for edge in list(location.edges_out(Selector(has_kind=Action))):
        if _has_tags(edge, "dynamic", "sandbox", "incremental"):
            graph.remove(edge.uid, _ctx=ctx)


def _incremental_action_payload(host: HasGame, move: IncrementalMove) -> dict:
    duration = 1 if move.kind == "end_cycle" else 0
    return {
        "sandbox_incremental_game": host.uid,
        "move": move,
        "sandbox_time_cost": SandboxTimeCost(
            kind="resource_cycle" if move.kind == "end_cycle" else "resource_allocation",
            duration=duration,
        ),
    }


def _host_from_payload(location: SandboxLocation, payload: dict) -> HasGame:
    host_id = payload["sandbox_incremental_game"]
    if not isinstance(host_id, UUID):
        raise TypeError("sandbox_incremental_game payload must be a UUID")
    host = location.graph.get(host_id)
    if not isinstance(host, HasGame):
        raise TypeError("sandbox_incremental_game payload must reference a HasGame node")
    if not isinstance(host.game, IncrementalGame):
        raise TypeError("sandbox_incremental_game payload must reference an IncrementalGame")
    if not isinstance(host.game_handler, IncrementalGameHandler):
        raise TypeError(
            "sandbox_incremental_game payload must reference an IncrementalGameHandler"
        )
    return host


def _latest_fragments(host: HasGame) -> list[ContentFragment]:
    fragments = host.game_handler.get_journal_fragments(host.game)
    if fragments is None:
        return []
    return [
        fragment
        for fragment in fragments
        if isinstance(fragment, ContentFragment)
    ]


def _store_incremental_fragments(
    location: SandboxLocation,
    host: HasGame,
) -> None:
    fragments = _latest_fragments(host)
    if fragments:
        location.locals["_sandbox_incremental_fragments"] = fragments


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_incremental_game_moves(*, caller, ctx, **_kw):
    """Project hosted incremental-game moves as ordinary sandbox choices."""
    if not isinstance(caller, SandboxLocation):
        return None
    graph = caller.graph
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_incremental_actions(caller, ctx=ctx)

    for host in _hosted_incremental_games(caller):
        _ensure_incremental_ready(host)
        if host.game.phase != GamePhase.READY:
            continue
        if host.game.result.is_terminal:
            continue
        for move in host.game_handler.get_available_moves(host.game):
            label = host.game_handler.get_move_label(host.game, move)
            Action(
                registry=graph,
                label=f"sandbox_incremental_{host.get_label()}_{move.kind}_{move.target or 'cycle'}",
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=label,
                payload=_incremental_action_payload(host, move),
                tags={"dynamic", "sandbox", "incremental"},
                ui_hints={
                    "source": "sandbox_incremental_game",
                    "contribution": "resource_allocation",
                    "source_label": host.get_label(),
                    "source_kind": "game",
                    "move": move.kind,
                    "target": move.target,
                },
            )
    return None


@on_update(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
    priority=Priority.NORMAL,
)
def process_sandbox_incremental_game_move(*, caller, ctx, **_kw):
    """Apply selected zero-duration allocation moves for hosted incremental games."""
    if not isinstance(caller, SandboxLocation):
        return None
    payload = ctx.selected_payload
    if not isinstance(payload, dict) or "sandbox_incremental_game" not in payload:
        return None

    move = payload["move"]
    if not isinstance(move, IncrementalMove):
        raise TypeError("sandbox incremental move payload must be an IncrementalMove")
    if move.kind == "end_cycle":
        return None

    host = _host_from_payload(caller, payload)
    _ensure_incremental_ready(host)
    host.game_handler.receive_move(host.game, move)
    if host.game.history:
        host.locals["last_round"] = host.game.history[-1]
        host.locals["round_result"] = host.game.history[-1].result
    else:
        host.locals["last_round"] = None
        host.locals["round_result"] = None
    host.locals["game_result"] = host.game.result
    _store_incremental_fragments(caller, host)
    return None


@on_sandbox_tick(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def reconcile_incremental_games_on_sandbox_tick(*, caller, ctx, clock_tick, **_kw):
    """Tick observer that resolves one cycle for hosted incremental games."""
    if not isinstance(caller, SandboxLocation):
        return None

    events: list[SandboxTickEvent] = []
    for host in _hosted_incremental_games(caller):
        if host.locals.get("_sandbox_incremental_last_tick") == clock_tick:
            continue
        _ensure_incremental_ready(host)
        if host.game.phase != GamePhase.READY:
            continue
        if host.game.result.is_terminal:
            continue
        host.game_handler.resolve_cycle_tick(host.game)
        host.locals["_sandbox_incremental_last_tick"] = clock_tick
        if host.game.history:
            host.locals["last_round"] = host.game.history[-1]
            host.locals["round_result"] = host.game.history[-1].result
        host.locals["game_result"] = host.game.result
        for fragment in _latest_fragments(host):
            events.append(
                SandboxTickEvent(
                    kind="incremental_cycle",
                    source_label=host.get_label(),
                    text=fragment.content,
                    clock_tick=clock_tick,
                )
            )
    return events or None


@on_journal(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
    priority=Priority.LATE,
)
def render_sandbox_incremental_journal(*, caller, ctx, **_kw):
    """Append allocation-action journal fragments for hosted incremental games."""
    if not isinstance(caller, SandboxLocation):
        return None
    additions = caller.locals.get("_sandbox_incremental_fragments")
    if not isinstance(additions, list):
        return None
    caller.locals["_sandbox_incremental_fragments"] = []
    return additions or None


__all__ = [
    "process_sandbox_incremental_game_move",
    "project_sandbox_incremental_game_moves",
    "render_sandbox_incremental_journal",
    "reconcile_incremental_games_on_sandbox_tick",
]
