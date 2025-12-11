
from __future__ import annotations
from typing import *
from pprint import pformat

from .story_node import StoryNode
if TYPE_CHECKING:  # pragma: no cover
    StoryNode_ = StoryNode
else:
    StoryNode_ = object
from .runtime import RuntimeMixin

import attr

@StoryNode.define
class NodeReference(RuntimeMixin, StoryNode):

    #: Do not use directly, access via `follow`
    _next: str = attr.ib(default=None,
                         metadata={'consumes_str': True})
                         # validator=attr.validators.instance_of( (str, StoryNode) ))
    done: bool = attr.ib( default=False )

    def follow(self) -> TraversableMixin | None:
        if self._next is None:
            print( f"WARNING: {self.path} has no _next!!")
            if self.uid is None:
                print( pformat( self.as_dict() ) )
            return

        if isinstance(self._next, TraversableMixin):
            return self._next

        elif isinstance(self._next, str):
            # Check for _next is path/eid and _next is peer in scene
            candidates = [self._next, f"{self.root.uid}/{self._next}"]
            for c in candidates:
                try:
                    res = self.context[c]
                    return res
                except KeyError as e:
                    pass

        raise KeyError( self.path, self._next )

    def apply(self, **kwargs):
        if self.done:
            self.root.visit(done=True)


@StoryNode.define
class TraversableMixin(RuntimeMixin):

    _visited: int = -1
    repeats: bool = False
    num_visits: int = 0

    def visit(self, done=False):
        self._visited = self.context.now
        self.num_visits += 1
        if done and self.world:
            self.world.done( self )

    @property
    def completed(self):
        return not self.repeats and self.num_visits > 0

    @property
    def turns_since(self) -> int:
        if self._visited >= 0:
            return self.context.now - self._visited
        return -1

    def avail(self, **kwargs) -> bool:
        """Checks if traversable is completed"""
        if not super().avail(**kwargs):
            # print('failed traversable super')
            return False
        if self._dirty:
            return True
        return not self.completed
        # not( x and y ) = not x or not y, de morgan's

    continues: List[NodeReference] = attr.ib( factory=list, metadata={'auto_uid': "cnt{i:02d}"} )
    def continue_(self, **kwargs) -> TraversableMixin:
        for ref in self.continues:
            if ref.avail(**kwargs):
                if ref.follow() is None:
                    print(f"Failed to follow continue ref")
                    print(pformat(ref.as_dict()))
                return ref.follow()

    redirects: List[NodeReference] = attr.ib(factory=list)
    def redirect(self, **kwargs) -> TraversableMixin:
        for ref in self.redirects:
            if ref.avail(**kwargs):
                if ref.follow() is None:
                    print(f"Failed to follow redirect ref")
                    print(pformat(ref.as_dict()))
                return ref.follow()
        # check for general redirects on parent entities
        if hasattr(self.parent, 'redirect'):
            return self.parent.redirect()


@StoryNode.define
class Traversable(TraversableMixin, RuntimeMixin, StoryNode):
    pass
