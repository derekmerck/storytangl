
from __future__ import annotations
from typing import *
import inspect

import attr

if TYPE_CHECKING:  # pragma: no cover
    from .meta import EntityMeta
    from .entity import Entity

@attr.define
class EntityManager:

    uid: str = "def"

    _template_maps: Dict[str, Dict[str, Dict]] = attr.ib( factory=dict )
    def template_maps(self, base_cls: type(Entity)) -> dict:
        res = {}
        mro = [cls.__name__ for cls in reversed( base_cls.__mro__ )]
        for k, v in self._template_maps.items():
            if k in mro:
                res |= v
        return res

    _override_classes: Dict[str, type[Entity]] = attr.ib( factory=dict )
    def override_cls(self, base_cls: type[Entity] | str) -> type[Entity]:
        if inspect.isclass( base_cls ):
            key = base_cls.__name__
        elif isinstance( base_cls, str ):
            key = base_cls
        else:
            raise TypeError(f"No key for {base_cls} to coerce") # pragma: no cover

        if key in self._override_classes:
            return self._override_classes[ key ]
        if inspect.isclass( base_cls ):
            return base_cls
        raise TypeError(f"No override or default cls for {base_cls}")  # pragma: no cover

    #: classes to instantiate in a new collection
    new_collection_classes: List[type(Entity)] = attr.ib( factory=list )
    def new_collection(self) -> EntityMeta:
        """Create a new collection of entities with shared meta"""
        meta = EntityMeta( manager=self )
        for k in self.new_collection_classes:
            for kk, vv in self.template_maps(k.__name__):
                k( **vv, meta=meta )
        return meta

    def ns(self, **kwargs) -> dict:
        res = {"manager": self}
        return res
