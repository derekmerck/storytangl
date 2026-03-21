# tangl/core/selector.py
"""Query selectors for entity collections.

Selectors are pure predicate objects used to query entities and registries without
embedding matching logic on entity classes. This is the v38 replacement for legacy
``Entity.matches(**criteria)`` style matching.

See Also
--------
:class:`tangl.core.registry.Registry`
    ``find_all(selector=...)`` and ``chain_find_all(...)`` consume selectors.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Iterator, Self, Type, TypeVar

from pydantic import BaseModel

from tangl.type_hints import Identifier

from .entity import Entity

ET = TypeVar("ET", bound=Entity)


class Selector(BaseModel, extra="allow"):
    """Pure query predicate model for matching entities.

    Why
    ---
    Selectors decouple query criteria from entity implementation. Entities expose
    attributes and predicate-like methods; selectors provide reusable matching logic.

    Key Features
    ------------
    - ``Selector`` is a Pydantic model, not an :class:`Entity`.
    - ``predicate`` stores an optional custom callable pre-check.
    - With ``extra=\"allow\"``, all criteria kwargs beyond ``predicate`` are stored in
      ``__pydantic_extra__`` and interpreted by :meth:`matches`.

    Notes
    -----
    - Criterion value ``typing.Any`` is a wildcard and is skipped.
    - ``None`` is *not* a wildcard; it is compared normally.
    - Any callable entity attribute is invoked with the criterion value, not only
      ``has_*`` / ``is_*`` names (those are conventions, not requirements).
    - Avoid properties that return callables on matchable names because selector
      callable detection is based on runtime ``callable(...)`` checks.

    Example:
        >>> class E(Entity):
        ...     @property
        ...     def label_rev(self):
        ...         return self.label[::-1]
        >>> e = E(label="abc")
        >>> Selector(
        ...     predicate=lambda x: x.label == "abc",
        ...     label="abc",
        ...     has_kind=E,
        ...     label_rev="cba",
        ... ).matches(e)
        True

        >>> s = Selector(has_identifier="abc")
        >>> f = E(label="def")
        >>> list(s.filter([e, f]))
        [<E:abc>]
    """

    predicate: Callable[[Entity], bool] | None = None

    def filter(self, entities: Iterable[ET]) -> Iterator[ET]:
        """Lazily filter an iterable of entities with this selector."""
        return filter(self.matches, entities)

    def matches(self, entity: Entity) -> bool:
        """Return ``True`` when ``entity`` satisfies all selector criteria.

        Matching algorithm:

        1. Evaluate ``predicate`` first, if provided.
        2. Iterate ``__pydantic_extra__`` criteria.
        3. For each criterion:
           - skip if value is ``typing.Any``;
           - fail if entity is missing the named attribute;
           - call attribute(value) when the attribute is callable;
           - otherwise compare by equality.

        Missing attributes are a hard non-match. Callable attributes receive the
        criterion as their sole argument (for example ``has_tags({"a"})``).
        """
        if self.predicate is not None and not self.predicate(entity):
            return False

        for attrib_name, target_val in (self.__pydantic_extra__ or {}).items():
            if target_val is Any:
                continue
            if attrib_name in {"identifier", "alias"}:
                attrib_name = "has_identifier"
            if attrib_name in {"is_instance", "has_kind"}:
                if hasattr(entity, attrib_name):
                    attrib_value = getattr(entity, attrib_name)
                    if callable(attrib_value):
                        if not attrib_value(target_val):
                            return False
                        continue
                if not isinstance(entity, target_val):
                    return False
                continue
            if not hasattr(entity, attrib_name):
                return False
            attrib_value = getattr(entity, attrib_name)
            if callable(attrib_value):
                if not attrib_value(target_val):
                    return False
            elif attrib_value != target_val:
                return False
        return True

    def with_defaults(self, **criteria: Any) -> Selector:
        """Return a copy with non-conflicting defaults added.

        Existing criteria are preserved; new keys are added only when this selector
        does not already expose them as fields or extras.

        Example:
            >>> s = Selector(label="abc")
            >>> s2 = s.with_defaults(label="xyz", has_kind=Entity)
            >>> s2.label
            'abc'
            >>> s2.has_kind is Entity
            True
        """
        for key in list(criteria.keys()):
            if hasattr(self, key):
                criteria.pop(key)
        return self.model_copy(update=criteria)

    def with_criteria(self, **criteria: Any) -> Selector:
        """Return a copy with overriding criteria.

        Most criteria overwrite existing values. ``has_kind`` is special-cased to
        prevent widening: replacement is applied only when the new kind is a subclass
        of the existing one.

        Example:
            >>> class P(Entity):
            ...     pass
            >>> class C(P):
            ...     pass
            >>> Selector(has_kind=C).with_criteria(has_kind=P).has_kind is C
            True
            >>> Selector(has_kind=P).with_criteria(has_kind=C).has_kind is C
            True
        """
        if "has_kind" in criteria and hasattr(self, "has_kind"):
            if not issubclass(criteria["has_kind"], self.has_kind):
                criteria.pop("has_kind")
        return self.model_copy(update=criteria)

    @classmethod
    def from_identifier(cls, identifier: Identifier) -> Self:
        """Build ``Selector(has_identifier=identifier)``."""
        return cls(has_identifier=identifier)

    from_id = from_identifier

    @classmethod
    def from_kind(cls, kind: Type[ET]) -> Self:
        """Build ``Selector(has_kind=kind)``."""
        return cls(has_kind=kind)

    @classmethod
    def chain_or(cls, *selectors: Selector) -> Selector:
        """Return a ChainedOrSelector.

        Example:
            >>> class P(Entity):
            ...     foo: str = "bar"
            >>> s = Selector.chain_or(Selector(foo="bar"), Selector(foo="baz"))
            >>> s.matches(P())
            True
            >>> s.matches(P(foo="baz"))
            True
        """
        class ChainedOrSelector(Selector):
            selectors: tuple[Selector, ...]

            def matches(self, entity: Entity) -> bool:
                if not super().matches(entity):
                    return False
                return any(selector.matches(entity) for selector in self.selectors)

        return ChainedOrSelector(selectors=selectors)
