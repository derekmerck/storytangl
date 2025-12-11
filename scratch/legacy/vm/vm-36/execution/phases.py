# tangl/vm/phases.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Dict, List, Tuple, Iterable

class Phase(IntEnum):
    VALIDATE = 10
    EXECUTE  = 20
    JOURNAL  = 30

# Handlers take a StepContext; they should only emit effects/fragments (no direct mutation)
Handler = Callable[["StepContext"], None]
Predicate = Callable[["StepContext"], bool]


# @dataclass
# class PhaseBus:
#     _reg: Dict[Phase, List[Tuple[int, str, Handler]]] = field(default_factory=dict)
#
#     def register(self, phase: Phase, handler_id: str, prio: int, fn: Handler, predicate: Predicate = None) -> None:
#         self._reg.setdefault(phase, []).append((prio, handler_id, fn))
#         self._reg[phase].sort(key=lambda t: t[0])
#
#     def register_predicated(self, phase: Phase, handler_id: str, prio: int,
#                             predicate: Predicate, fn: Handler) -> None:
#         """
#         Usage:
#         1) “all nodes during JOURNAL”
#         >>> bus.register_predicated(Phase.JOURNAL, "all/journal_banner", 10,
#         ...         predicate=lambda ctx: True,
#         ...         fn=lambda ctx: ctx.say({"type":"text","text":"— Scene break —"}))
#
#         2) “nodes authored by X” (tags or attrs)
#         >>> bus.register_predicated(Phase.JOURNAL, "by:alice", 50,
#         ...         predicate=lambda ctx: getattr(ctx, "cursor_label", None) in {"fabula:alice"},
#         ...         fn=lambda ctx: ctx.say({"type":"note","who":"alice"}))
#
#         3) “any node with a blackjack ancestor”
#         >>> bus.register_predicated(Phase.EXECUTE, "bj/turn", 50,
#         ...     predicate=lambda ctx: "blackjack" in ctx.active_domains,
#         ...     fn=lambda ctx: ctx.say({"type":"debug","text":"BJ turn…"}))
#         """
#         def guarded(ctx: "StepContext"):
#             if predicate(ctx):
#                 fn(ctx)
#         self.register(phase, handler_id, prio, guarded)
#
#     def run(self, phase: Phase, ctx: "StepContext",
#             extra: Iterable[Tuple[int, str, Handler]] = ()) -> None:
#         """
#         Execute handlers for `phase`, merging in:
#           1) globally-registered handlers (self._reg[phase])
#           2) scope-local handlers on the StepContext (ctx.scope_handlers[phase]) if present
#           3) optional `extra` overlay passed by caller
#         Ordering is by (priority asc), then source group: global < scope < extra,
#         then handler_id for stability.
#         """
#         global_list = list(self._reg.get(phase, []))
#         if ctx.scope:
#             phase_scope_handlers = ctx.scope.handlers_by_phase().get(phase, ())
#         else:
#             phase_scope_handlers = []
#
#         # scope_by_phase = getattr(ctx, "scope_handlers", {}) or {}
#         # scope_list = list(scope_by_phase.get(phase, ()))
#         extra_list = list(extra)
#
#         merged: List[Tuple[int, int, str, Handler]] = []
#         for source_idx, lst in enumerate((global_list, phase_scope_handlers, extra_list)):
#             for prio, hid, fn in lst:
#                 merged.append((prio, source_idx, hid, fn))
#
#         merged.sort(key=lambda t: (t[0], t[1], t[2]))  # prio, source, handler_id
#
#         for prio, _src, hid, fn in merged:
#             ctx._handler = (phase.name, hid)
#             fn(ctx)
#         ctx._handler = None

class PhaseBus:
    def __init__(self):
        # { phase: [(id, prio, fn), ...] }
        self._handlers: dict[Phase, list[tuple[str,int,Callable]]] = {p: [] for p in Phase}

    def register(self, phase: Phase, handler_id: str, priority: int, fn: Callable):
        self._handlers[phase].append((handler_id, priority, fn))

    def register_predicated(self, phase: Phase, handler_id: str, prio: int,
                            predicate: Predicate, fn: Handler) -> None:
        """
        Usage:
        1) “all nodes during JOURNAL”
        >>> bus.register_predicated(Phase.JOURNAL, "all/journal_banner", 10,
        ...         predicate=lambda ctx: True,
        ...         fn=lambda ctx: ctx.say({"type":"text","text":"— Scene break —"}))

        2) “nodes authored by X” (tags or attrs)
        >>> bus.register_predicated(Phase.JOURNAL, "by:alice", 50,
        ...         predicate=lambda ctx: getattr(ctx, "cursor_label", None) in {"fabula:alice"},
        ...         fn=lambda ctx: ctx.say({"type":"note","who":"alice"}))

        3) “any node with a blackjack ancestor”
        >>> bus.register_predicated(Phase.EXECUTE, "bj/turn", 50,
        ...     predicate=lambda ctx: "blackjack" in ctx.active_domains,
        ...     fn=lambda ctx: ctx.say({"type":"debug","text":"BJ turn…"}))
        """
        def guarded(ctx: "StepContext"):
            if predicate(ctx):
                fn(ctx)
        self.register(phase, handler_id, prio, guarded)

    def run(self, phase: Phase, ctx):
        # 1) start with bus-registered handlers
        merged: list[tuple[str,int,Callable]] = list(self._handlers.get(phase, []))

        # 2) merge scope-provided handlers for this phase
        # prefer a precomputed overlay if present, else filter from scope.handlers
        scope = getattr(ctx, "scope", None)
        if scope:
            by_phase = getattr(ctx, "scope_handlers_by_phase", None)
            if by_phase and phase in by_phase():
                merged.extend(by_phase()[phase])          # already (id, prio, fn)
            else:
                for (ph, hid, prio, fn) in getattr(scope, "handlers", []):
                    if ph == phase:
                        merged.append((hid, prio, fn))

        # 3) stable order
        merged.sort(key=lambda t: (t[1], t[0]))

        # 4) dispatch with provenance
        for hid, _, fn in merged:
            ctx._handler = (phase.name, hid)
            fn(ctx)
        if hasattr(ctx, "_handler"):
            delattr(ctx, "_handler")