from tangl.core.entity import Entity, Graph
from tangl.core.handler.context import on_gather_context


class TamperEvident(Entity):

    dirty: bool = False
    # flag for when the entity has been tampered with via a non-rule-based mechanism

    @property
    def is_dirty(self) -> bool:
        if isinstance(self, Graph):
            return getattr(self, "dirty", False) or \
                any([getattr(node, "dirty", False) for node in self])
        return self.dirty

    @on_gather_context.register()
    def _provide_is_dirty(self):
        # This should have its own `any_true` pipeline, but we can do it
        # more simply but just only returning a value on True, otherwise
        # None will be ignored when the context is flattened.  If we return
        # False, a late False could clobber an earlier True.
        if self.is_dirty:
            return {'dirty': True}
