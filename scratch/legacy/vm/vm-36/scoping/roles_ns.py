# tangl/vm/scoping/roles_ns.py
from collections.abc import Mapping
from tangl.core36.graph import Graph
from tangl.core36.types import EdgeKind

# todo: inject aliases into ns, note 'role' is only one of several alias triggers

class RoleNamespace(Mapping):
    """Read-only mapping 'alias' -> Node (or thin proxy), derived from role edges."""
    def __init__(self, graph: Graph, bindings: dict[str, str]):  # alias -> uid
        self._g = graph
        self._b = bindings

    def __getitem__(self, key):
        uid = self._b[key]
        return self._g.get(uid)  # or return an immutable/proxy if you prefer

    def __iter__(self):
        return iter(self._b)

    def __len__(self):
        return len(self._b)

def compute_role_bindings(graph: Graph, owner_uid) -> dict[str, str]:
    """Scan owner’s outbound role edges and return alias -> target_uid."""
    out = {}
    for eid in graph.find_edge_ids(src=owner_uid):
        e = graph.get(eid)
        kind = getattr(e, "kind", "")
        if kind.startswith(EdgeKind.ROLE.prefix()):  # "role:"
            alias = kind[len(EdgeKind.ROLE.prefix()):]
            target = getattr(e, "dst_id", None) or getattr(e, "dst", None)
            if target:
                out[alias] = target
    return out