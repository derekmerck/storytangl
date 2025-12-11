
from typing import *

import attr

from .entity import Entity

if TYPE_CHECKING:  # pragma: no coverage
    Entity_ = Entity
else:
    Entity_ = object

from .runtime import Conditional_, Applyable_

@attr.define( slots=False, init=False, eq=False, hash=False )
class EntityReference(Conditional_, Applyable_, Entity):

    next: Optional[Union[str, 'Traversable_']] = attr.ib(default=None, metadata={"consumes_str": True})
    done: bool = False

    def deref(self) -> 'Traversable_':
        if not self.next:
            return None
        if isinstance(self.next, str):
            candidates = [self.next, f"{self.root.uid}/{self.next}"]
            for c in candidates:
                try:
                    res = self.ctx[c]
                    return res
                except KeyError as e:
                    pass
        elif isinstance(self.next, Traversable_):
            return self.next
        print( self.ctx.keys() )
        raise KeyError(f"Can't dereference {self.next}")

    # this would provide a partial solution to redirecting the namespce for eval,
    # but not for render...
    # def check(self, **kwargs):
    #     # Redirect avail to reference entity
    #     print(f"checking avail on ref")
    #     if self.deref():
    #         print(f"checking avail on {self.next}")
    #         if not self.deref().check(**kwargs):
    #             print(f"Unavailable")
    #             return False
    #         print(f"Going on to check self")
    #     return super().check(**kwargs)

    def avail(self, **kwargs):
        if self.locals.get("avail") == "ignore":
            return True
        if not super().avail( **kwargs ):
            return False
        def _test():
            if self.deref() and self.deref() != self.parent:
                if not self.deref().avail( ** kwargs):
                    return False
            return True
        return _test() or self.forced

    def apply(self, **kwargs):
        if self.done:
            self.root.visit()
        super().apply(**kwargs)

@attr.define( slots=False, init=False, eq=False, hash=False )
class Traversable_(Entity_):

    redirects: List[EntityReference] = attr.ib( factory=list )
    continues: List[EntityReference] = attr.ib( factory=list )

    def redirect(self) -> 'Traversable_':
        for el in self.redirects:
            if el.avail():
                return el.deref()

    def continue_(self) -> 'Traversable_':
        for el in self.continues:
            if el.avail():
                return el.deref()

    _num_visits: int = 0
    _visit_turn: int = 0  # turn

    def visit(self):
        self._num_visits += 1
        if self.ctx and hasattr(self.ctx, "turn"):
            self._visit_turn = self.ctx.turn

    @property
    def visited(self):
        return self._num_visits > 0

    @property
    def num_visits(self) -> int:
        return self._num_visits

    @property
    def turns_since(self):
        if not self.visited:
            return -1
        if self.ctx and hasattr(self.ctx, "turn"):
            return self.ctx.turn - self._visit_turn

    repeats: bool = False  # visit more than once?

    @property
    def completed(self):
        return not self.repeats and self.visited

    def avail(self, **kwargs) -> bool:  # implies a cascading check of all conditions
        if self.locals.get("avail") == "ignore":
            return True
        if not super().avail( **kwargs ):
            return False
        return not self.completed or self.forced
