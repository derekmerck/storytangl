# tangl/core/facts.py
"""
# tangl.core.facts

Small, recomputable **derived indexes** over a `Graph` used by guards, scope assembly,
and light queries. Facts are **read-only** and built via `Facts.compute(graph)`.

**Why recompute instead of incremental?**
For the MVP, the graph per tick is small and recompute keeps the code obvious and correct.
If/when we need it, a targeted incremental `apply_effect(...)` can update just the
indexes we use in hot paths (e.g., label/tag maps and `contains` ancestry).

**Scope conventions**
- A structural scope is a tree over edges with kind `"contains"`.
- Domain activation is opt-in via node/ancestor tags `domain:*` (see `active_domains_along`).
- `vm.scopes.assemble_namespace` consumes `Facts` to build the ChainMap and mount handlers.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from .graph import Graph
from .entity import Node, GraphItem

_DOMAIN_PREFIX = "domain:"

# todo suggestion: Make Facts stronger
#
# @dataclass
# class StructuralIndex:
#     parent_of: dict[UUID, UUID]
#     children_of: dict[UUID, set[UUID]]
#
# @dataclass
# class Facts:
#     labels: dict[str, UUID]
#     tags: dict[str, set[UUID]]
#     structure: StructuralIndex
#     # .compute(g) builds these; existing call sites unchanged

@dataclass(frozen=True)
class Facts:
    """
    Derived indexes:

    - `label_idx`: `label → uid`
    - `tags_idx`: `tag → {uid}`
    - `parent_of` / `children_of`: ancestry from `"contains"` edges
    - `domains_on`: `node_uid → {"dialogue", "blackjack", ...}` from `tags` prefixed with `domain:`

    **Why this exact set?**
    It’s the minimum to support:
    - fast label lookups in author code/tests,
    - **scope assembly** by ancestor chain (`parent_of`),
    - **domain mounting** along the chain (`active_domains_along`).

    The VM can add more views later (role indexes, affordance indexes) without changing the contract.
    """
    label_idx: dict[str, UUID]
    tags_idx: dict[str, set[UUID]]
    # structure
    parent_of: dict[UUID, UUID]            # child -> parent for kind="contains"
    children_of: dict[UUID, set[UUID]]     # parent -> children
    # domain mounts (by node)
    domains_on: dict[UUID, set[str]]

    @classmethod
    def compute(cls, g: Graph) -> Facts:
        """
        Build all indexes from the current surface graph.

        Called:
        - at tick start (base graph),
        - optionally against a **preview** graph (read-your-writes) between phases.
        """
        label_idx: dict[str, UUID] = {}
        tags_idx: dict[str, set[UUID]] = {}
        parent_of: dict[UUID, UUID] = {}
        children_of: dict[UUID, set[UUID]] = {}
        domains_on: dict[UUID, set[str]] = {}

        # nodes: labels/tags/locals/domains
        for it in g.items:
            if isinstance(it, Node):
                if it.label:
                    label_idx[it.label] = it.uid
                for t in it.tags:
                    tags_idx.setdefault(t, set()).add(it.uid)
                    if t.startswith(_DOMAIN_PREFIX):
                        domains_on.setdefault(it.uid, set()).add(t[len(_DOMAIN_PREFIX):])

        # edges: structure ("contains")
        for e in g.edges():
            if e.kind == "contains":
                parent_of[e.dst_id] = e.src_id
                children_of.setdefault(e.src_id, set()).add(e.dst_id)

        return cls(label_idx, tags_idx, parent_of, children_of, domains_on)

    # convenience
    def by_label(self, label: str) -> Optional[UUID]:
        return self.label_idx.get(label)

    def with_tag(self, tag: str) -> set[UUID]:
        return self.tags_idx.get(tag, set())

    def parent(self, uid: UUID) -> Optional[UUID]:
        return self.parent_of.get(uid)

    def ancestors(self, uid: UUID) -> list[UUID]:
        """
        Return the **ancestor chain** for `uid` by following `parent_of` until the root,
        nearest ancestor first. Used to layer structural scopes (`locals`) and collect domains.
        """
        out: list[UUID] = []
        cur = uid
        while cur in self.parent_of:
            p = self.parent_of[cur]
            out.append(p)
            cur = p
        return out

    def active_domains_along(self, uid: UUID) -> set[str]:
        """
        Union of domain names (from `tags` with prefix `domain:`) on the node and its ancestors.

        This is the sole source of **domain activation** for `vm.scopes`. Providers are then resolved
        via `DomainRegistry` and merged parent-before-child for deterministic overrides.
        """
        act: set[str] = set()
        if uid in self.domains_on:
            act |= self.domains_on[uid]
        for a in self.ancestors(uid):
            act |= self.domains_on.get(a, set())
        return act
