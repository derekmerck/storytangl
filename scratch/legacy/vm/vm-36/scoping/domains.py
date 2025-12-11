from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Mapping, Callable, Iterable, TYPE_CHECKING
from collections import defaultdict, deque

if TYPE_CHECKING:
    from tangl.vm36.execution import StepContext, Phase

@dataclass
class DomainDef:
    name: str
    parents: tuple[str, ...] = ()
    provider: object = None  # may expose: vars(), handlers(), finders(), builders(), templates()


@dataclass
class DomainRegistry:
    """
    Map domain name -> provider object with vars() and handlers().
    Domain DAG (name -> DomainDef).
    """
    defs: dict[str, DomainDef] = field(default_factory=dict)

    def add(self, name: str, *, parents: Iterable[str] = (), provider: object):
        self.defs[name] = DomainDef(name=name, parents=tuple(parents), provider=provider)

    def linearize(self, active: Iterable[str]) -> list[str]:
        """Close over parents and return a deterministic topological order:
           parents before children; ties by name."""
        # close
        want: set[str] = set(active)
        q = deque(active)
        while q:
            cur = q.popleft()
            for p in self.defs.get(cur, DomainDef(cur)).parents:
                if p not in want:
                    want.add(p); q.append(p)
        # topo (Kahn)
        indeg: Dict[str, int] = {n: 0 for n in want}
        children: Dict[str, list[str]] = defaultdict(list)
        for n in want:
            for p in self.defs.get(n, DomainDef(n)).parents:
                if p in want:
                    indeg[n] += 1
                    children[p].append(n)
        ready = sorted([n for n, d in indeg.items() if d == 0])
        order: list[str] = []
        while ready:
            n = ready.pop(0)
            order.append(n)
            for c in sorted(children.get(n, [])):
                indeg[c] -= 1
                if indeg[c] == 0:
                    ready.append(c); ready.sort()
        if len(order) != len(want):
            raise ValueError("Domain inheritance cycle detected among: " + ", ".join(sorted(want)))
        return order

    # helpers to call provider
    def _vars(self, name, g, node) -> Mapping[str, object]:
        p = self.defs[name].provider
        return getattr(p, "vars", lambda g, n: {})(g, node)

    def _handlers(self, name, g, node) -> Iterable[tuple[Phase, str, int, Callable[[StepContext], None]]]:
        p = self.defs[name].provider
        return getattr(p, "handlers", lambda g, n: ())(g, node)

    def _templates(self, name, g, node):
        p = self.defs[name].provider
        return getattr(p, "templates", lambda g, n: ()) (g, node)

    def _finders(self, name, g, node):
        p = self.defs[name].provider
        return getattr(p, "finders", lambda g, n: ()) (g, node)

    def _builders(self, name, g, node):
        p = self.defs[name].provider
        return getattr(p, "builders", lambda g, n: ()) (g, node)
