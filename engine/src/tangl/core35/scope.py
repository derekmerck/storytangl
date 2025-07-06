from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List, TYPE_CHECKING

from pyrsistent import pmap, PMap

from .behaviors.behavior_registry import BehaviorRegistry, _NOOP_BEHAVIOR

@dataclass(frozen=True, slots=True)
class ScopeMeta:
    id: str
    parent: Optional[str]      # None for root
    # later: source_node, sink_node

class ScopeTree:
    def __init__(self, mapping: Dict[str, ScopeMeta]):
        self.meta = mapping    # id → ScopeMeta

    def is_ancestor(self, anc: str, desc: str) -> bool:
        while desc and desc != anc:
            desc = self.meta[desc].parent
        return desc == anc

    def lca(self, a: str, b: str) -> str:
        ancestors = set()
        while a:
            ancestors.add(a)
            a = self.meta[a].parent
        while b not in ancestors:
            b = self.meta[b].parent
        return b

def build_scope_tree(nodes) -> ScopeTree:
    metas = {}
    for n in nodes.values():
        metas.setdefault(n.scope_id, ScopeMeta(id=n.scope_id, parent=None))
    # naive: every scope except "root" has parent "root"
    for s in metas.values():
        if s.id != "root" and s.parent is None:
            metas[s.id] = ScopeMeta(id=s.id, parent="root")
    return ScopeTree(metas)

@dataclass(slots=True)
class Layer:
    scope_id: str
    locals: PMap = field(default_factory=pmap)
    behaviors: BehaviorRegistry = field(default_factory=BehaviorRegistry)

class LayerStack:
    def __init__(self):
        self._stack: list[Layer] = []

    # -------------------------------------------------
    def top(self) -> Layer:
        return self._stack[-1]

    def push(self, layer: Layer):
        self._stack.append(layer)

    def pop(self) -> Layer:
        return self._stack.pop()

    # -------------------------------------------------
    def lookup_behavior(self, key: str):
        for layer in reversed(self._stack):   # top → root
            try:
                return layer.behaviors.get_best(key)
            except KeyError:
                print(f"No behavior on {layer.scope_id} for phase {key}")
                continue
        return _NOOP_BEHAVIOR

    # "villain.hp" → ("villain","hp") split once
    def lookup_var(self, dotted: str, state: PMap | None = None):
        head, *rest = dotted.split(".", 1)
        tail = rest[0] if rest else None

        for layer in reversed(self._stack):          # top → root
            if head in layer.locals:
                val = layer.locals[head]
                return val[tail] if tail else val    # recurse on PMap

        if state is not None and head in state:
            val = state[head]
            return val[tail] if tail else val

        raise KeyError(dotted)


class ScopeManager:
    def __init__(self, tree: ScopeTree, stack: LayerStack):
        self.tree  = tree
        self.stack = stack

    def switch(self, curr_scope: str, next_scope: str):
        lca = self.tree.lca(curr_scope, next_scope)

        # unwind
        while self.stack.top().scope_id != lca:
            self.stack.pop()     # could call on_exit hooks later

        # wind
        path: List[str] = []
        s = next_scope
        while s != lca:
            path.append(s)
            s = self.tree.meta[s].parent
        for scope_id in reversed(path):
            self.stack.push(Layer(scope_id=scope_id))
