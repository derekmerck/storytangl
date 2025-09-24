# structural scopes are inferred from an anchor node according to ancestors on a graph.
# for example, ancestors can have their own templates/vars and less frequently, handlers.

# structural domains are mutable b/c they live on the graph, unlike affiliate
# domains, which are frozen because they may be shared across all stories

from tangl.core.graph import GraphItem
from .domain import Domain

class StructuralDomain(GraphItem, Domain):
    ...
