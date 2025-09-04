# tangl/vm/scoping/scope.py
from __future__ import annotations
from dataclasses import dataclass, field
from collections import ChainMap
from typing import Callable, Mapping, Dict, List, Set, TYPE_CHECKING
from uuid import UUID

from tangl.core36 import Graph, Facts
from .domains import DomainRegistry

if TYPE_CHECKING:
    from tangl.vm36.execution import StepContext, Phase
    from tangl.vm36.planning import OfferProvider

@dataclass(frozen=True)
class Scope:
    """
    Unified view of what's visible at a cursor:
      - active_domains: domain names active at/above the cursor
      - ns: ChainMap of variables (local -> ancestors -> domains -> globals)
      - handlers: [(phase, handler_id, prio, fn)]
      - offer_providers: providers yielding Offers for frontier/discovery
      - resolvers_by_kind: provisioning Resolvers grouped by kind
    """
    ns: ChainMap
    handlers: List[tuple[Phase, str, int, Callable]]   # (Phase, handler_id, prio, fn)
    offer_providers: List[OfferProvider] = field(default_factory=list)
    resolvers_by_kind: Dict[str, List[object]] = field(default_factory=dict)
    active_domains: Set[str] = field(default_factory=set)
    cursor_uid: UUID | None = None
    cursor_label: str | None = None

    # ---- legacy/deprecated
    def handlers_by_phase(self):
        from collections import defaultdict
        by = defaultdict(list)
        for (phase, hid, prio, fn) in self.handlers:
            by[phase].append((hid, prio, fn))
        for ph in by:
            by[ph].sort(key=lambda t: t[1])
        return dict(by)

    @classmethod
    def assemble(cls,
                 g: Graph,
                 facts: Facts,
                 cursor_uid: UUID,
                 domains: DomainRegistry | None = None,
                 globals_ns: Mapping[str, object] | None = None):
        # passes
        # from .scope_assembler import assemble_scope
        # return assemble_scope(g, facts, cursor_uid, domains, globals_ns)

        # fails
        from .scope_builder import ScopeBuilder
        return ScopeBuilder(g, facts, cursor_uid, domains, globals_ns).build()

