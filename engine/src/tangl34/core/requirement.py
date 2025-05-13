from typing import Callable, Optional, Literal, Dict, Any

from .entity import Entity

class Requirement(Entity):
    within_scope: Any = None
    # todo: Do we need a case for this?  If unbounded, look through all possible scopes, but
    #       sometimes may require an already assigned member of the node-local, subgraph-local
    #       or domain scope.  Like a shopkeeper from this town should not be satisfied by a
    #       shopkeeper from the domain scope who is assigned in another town.
    predicate: Callable[[Dict[str, Any]], bool]

    # todo: predicate             -> a callable that takes a context map and returns a bool
    #       match(**criteria)     -> entity built-in f that checks to see if all criteria exist on the entity
    #                                a predicate can include match criteria for an entity
    #       condition             -> a _string_ that gets eval'd with a context map, a predicate or a
    #                                match criteria can include conditions

    # todo: A soft req could just have it's own low priority fallback provider that
    #       resolves if it can't be satisfied by ctx?

    kind: Literal["hard", "soft"] = "hard"
    fallback_text: Optional[str] = None  # Only for soft requirements

    def satisfied(self, ctx: Dict[str, Any]) -> bool:
        return self.predicate(ctx)

    def resolve(self, ctx: Dict[str, Any]) -> bool:
        return self.satisfied(ctx) or self.kind == "soft" # todo: or find a capability that can satisfy you
