from typing import TYPE_CHECKING

from ..graph import Node, Graph
from ..runtime import ProvisionRegistry, CapabilityCache

if TYPE_CHECKING:
    from ..type_hints import Context

def resolve(node: Node, graph: Graph, reg: ProvisionRegistry, cache: CapabilityCache, ctx: 'Context'):
    for req in node.requires:          # node.requires is just set[Requirement]
        cap = _find_or_create(req, node.tier, reg, ctx)
        graph.link(node.uid, cap.owner_uid, "satisfies")