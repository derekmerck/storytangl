
import copy
from typing import *
from functools import cache
import random

import attr
from .entity import Entity, Uid


T_en = NewType('T_en', Type[Entity])





def bases_dict(data: List):
    if isinstance(data, List):
        res = {}
        for cls in data:
            res[cls.__name__] = [cls]
        return res


@attr.define(hash=False)
class EntityFactory(Entity):
    """An entity factory has a specific type, a manager can have multiple
    factories for different types of entities"""

    bases: list[T_en] = attr.ib(factory=list,
                                converter=lambda x: isinstance(x, list) and x or [x])

    def ref_cls(self):
        if len(self.bases) == 1:
            return self.bases[0]
        res = attr.make_class(self.bases[0].__name__, {},
                              bases=(*reversed(self.bases),),
                              hash=False, eq=False, slots=False)
        return res

    templs: Dict = attr.ib(factory=dict)

    def keys(self):
        return self.templs.keys()

    # DO NOT add mixin classes after you have started making things or memoize
    # will return stale responses
    @cache
    def new_cls(self, *subtypes) -> T_en:
        cls_name = self.bases[0].__name__
        uid = "".join([s.lower() for s in subtypes])
        fields = {}
        for b in self.bases:
            fields = fields | attr.fields_dict(b)

        for k, v in fields.items():
            val = v.default
            for s in subtypes:
                templ = self.templs[s]
                val = templ.get(k) or val
            if k == "uid":
                val = uid
            converter = v.converter or self.reduce_value
            kwargs = { 'default': val,
                       'converter': converter,
                       'validator': v.validator,
                       'repr': v.repr,
                       'eq': v.eq,
                       'metadata': v.metadata }
            fields[k] = attr.ib( **kwargs )

        res = attr.make_class(cls_name, fields,
                              bases=(*reversed(self.bases),),
                              hash=False, eq=False, slots=False)

        return res

    def new_instance(self, *subtypes, **kwargs) -> Entity:
        subtypes = list(subtypes)
        kwargs = {**kwargs}
        if kwargs.get('subtypes'):
            subtypes_ = kwargs.pop('subtypes')
            if isinstance(subtypes_, str):
                subtypes_ = [subtypes_]
            subtypes += subtypes_
        new_cls = self.new_cls(*subtypes)
        # Pre-init hook to inject kwargs based on the subtype templates used
        if hasattr(new_cls, "__entity_preinit__"):
            kwargs = new_cls.__entity_preinit__( **kwargs )
        res = new_cls(**kwargs)
        return res

    def inflate_instance(self, uid: Uid = None, **kwargs) -> Entity:
        if uid:  # may be '' rather than None
            templ = copy.deepcopy(self.templs[uid])
            deep_merge(templ, kwargs)
        else:
            templ = kwargs
        res = self.ref_cls()( **templ )
        return res

    @classmethod
    def reduce_value(cls, value: Any) -> Any:
        if not value:
            return value
        if isinstance(value, list):
            value = random.choice( value )
        return value

    def __hash__(self):
        return super().__hash__()
