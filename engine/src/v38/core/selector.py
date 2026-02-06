# tangl/core/selector.py
from __future__ import annotations
from typing import Any, Iterator, TypeVar, Iterable, Callable, Type, Self

from pydantic import BaseModel

from tangl.type_hints import Identifier
from .entity import Entity

ET = TypeVar('ET', bound=Entity)

class Selector(BaseModel, extra="allow"):
    """
    Not an entity, transient logical construct, not serializable, just a namespace
    for 'matches' terms.

    Pure query predicate. NO satisfaction semantics.  Satisfaction can be more
    completely handled with a Requirement.

    Extras are allowed, whatever attributes are defined will be used as selection criteria.

    - Field with matching names will be compared directly with their target value
    - Methods should start with "is_", "has_" will be invoked and compared to their target value
    - todo: Any attribute may be postfixed by a handler "_eq", "_in", "_lt", etc.  This defines the comparator, '_eq' is default.  '_in' assumes the key value is an iterable, if it's a tuple of two floats, it's compared with v0 <= x <= v1, otherwise it uses x in value

    **Rules:**
    - `matches()` is side-effect free
    - `Selector` is serializable only if criteria are serializable
    - If runtime-only callables needed, use a separate type

    Example:
        >>> class E(Entity):
        ...     @property
        ...     def label_rev(self): return self.label[::-1]
        >>> e = E(label='abc')
        >>> Selector(predicate=lambda e: e.label == 'abc', # predicate
        ...          label='abc',                          # field
        ...          has_kind=E,                           # callable attrib
        ...          label_rev='cba').matches(e)           # property
        True
        >>> s = Selector(has_identifier="abc"); assert s.matches(e)
        >>> s.with_criteria(has_tags={'foo'}).matches(e)
        False
        >>> f = E(label='def')
        >>> list( s.filter([e, f]) )
        [<E:abc>]
    """
    # todo: suggests baking basic entity axes identifier, kind, tags into field definitions for type checking
    # todo: if a selector is serializable, predicate need to be a Predicate RuntimeOp

    predicate: Callable[[Entity], bool] = None

    def filter(self, entities: Iterable[ET]) -> Iterator[ET]:
        return filter(self.matches, entities)

    def matches(self, entity: Entity) -> bool:
        if self.predicate is not None and not self.predicate(entity):
            return False
        for attrib_name, target_val in self.__pydantic_extra__.items():
            if target_val is None:
                # Skip anything purposefully set to None in criteria
                continue
            if not hasattr(entity, attrib_name):
                return False
            attrib_value = getattr(entity, attrib_name)
            if callable(attrib_value):
                # it's a "has_" or "is_" callable, call with value
                if not attrib_value(target_val):
                    return False
            else:
                # it's field data
                if attrib_value != target_val:
                    return False
        return True

    def with_criteria(self, **criteria: Any) -> Selector:
        return self.model_copy(update=criteria)

    @classmethod
    def from_identifier(cls, identifier: Identifier) -> Self:
        return cls(has_identifier=identifier)

    @classmethod
    def from_kind(cls, kind: Type[ET]) -> Self:
        return cls(has_kind=kind)
