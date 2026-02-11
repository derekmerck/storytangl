# tangl/core/selector.py
from __future__ import annotations
from typing import Any, Iterator, TypeVar, Iterable, Callable, Type, Self

from pydantic import BaseModel

from tangl.type_hints import Identifier
from .entity import Entity

ET = TypeVar('ET', bound=Entity)

class Selector(BaseModel, extra="allow"):
    """
    Pure query predicate for selecting entities.

    A `Selector` is a *transient* logical object used by registries and other core utilities
    to filter collections. It has **no** satisfaction semantics (see `vm.requirement` for
    "must be satisfied" logic).

    ## What it matches

    Selection criteria are supplied as keyword arguments. Because `extra="allow"` is enabled,
    any criteria key is accepted and interpreted against the target entity:

    - **Fields / properties**: if the entity has an attribute with the same name and that
      attribute is not callable, it is compared by equality.
    - **Predicates**: if the entity attribute is callable (typically methods named
      `has_*` / `is_*`), it is called with the criterion value and must return truthy.
    - **Custom predicate**: `predicate: Callable[[Entity], bool]` is applied first.

    A criterion value of `Any` is treated as a wildcard (ignored).

    ## Important semantics

    - `matches()` is intended to be **side-effect free**.
    - Missing attributes are a **hard non-match** (no implicit `None`).
    - Callable attributes are treated as boolean predicates and must accept the criterion
      value as their single argument.

    ## Template matching caveat

    In v38, templates may expose *two* matching axes:

    - **template-kind**: what wrapper record the template is (e.g., `Snapshot`, `TemplateGroup`)
    - **payload-kind**: what entity kind the template would materialize

    When possible, avoid relying on the ambiguous `has_kind` implementation in template
    that conflates these axes.  The default mixed-mode is primarily for mixing
    potential objects defined by templates and live objects in the same query.

    Prefer explicit predicate names such as `has_template_kind` and `has_payload_kind`
    (defined on `core.template.EntityTemplate`) when selecting templates.

    ## Examples

    Basic field + callable matching:

        >>> class E(Entity):
        ...     @property
        ...     def label_rev(self):
        ...         return self.label[::-1]
        >>> e = E(label='abc')
        >>> Selector(
        ...     predicate=lambda x: x.label == 'abc',  # custom predicate
        ...     label='abc',                           # field
        ...     has_kind=E,                            # callable attribute
        ...     label_rev='cba',                       # property
        ... ).matches(e)
        True

    Filtering an iterable:

        >>> s = Selector(has_identifier='abc')
        >>> f = E(label='def')
        >>> list(s.filter([e, f]))
        [<E:abc>]

    """
    # todo: suggests baking basic entity axes identifier, kind,
    #       tags into field definitions for type checking
    # todo: if a selector is serializable, predicate need to
    #       be a Predicate RuntimeOp

    predicate: Callable[[Entity], bool] = None

    def filter(self, entities: Iterable[ET]) -> Iterator[ET]:
        return filter(self.matches, entities)

    def matches(self, entity: Entity) -> bool:
        if self.predicate is not None and not self.predicate(entity):
            return False
        for attrib_name, target_val in self.__pydantic_extra__.items():
            if target_val is Any:
                # Skip anything purposefully set to Any in criteria
                # Note, it will check target_val = None as a normal comparison
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
        # maybe if there is already a 'kind', only replace it if it's more or less specific?
        return self.model_copy(update=criteria)

    @classmethod
    def from_identifier(cls, identifier: Identifier) -> Self:
        return cls(has_identifier=identifier)

    from_id = from_identifier  # shorter alias

    @classmethod
    def from_kind(cls, kind: Type[ET]) -> Self:
        return cls(has_kind=kind)
