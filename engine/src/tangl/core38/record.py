# tangl/core/record.py
"""Immutable ordered records and append-only ordered registries.

This module defines :class:`Record` as a frozen, content-addressed artifact and
:class:`OrderedRegistry` as an append-only :class:`~tangl.core38.registry.Registry`
specialization with range slicing over a comparable sort-key space.

See Also
--------
:mod:`tangl.core38.bases`
    Record composition traits (:class:`HasContent`, :class:`HasOrder`).
:mod:`tangl.core38.registry`
    Base registry behavior, selector filtering, and mapping semantics.
"""

from __future__ import annotations

from typing import Any, Callable, ClassVar, Iterable, Iterator, TypeVar, Union

from pydantic import ConfigDict, Field, ValidationError

from tangl.type_hints import Identifier

from .bases import HasContent, HasOrder
from .entity import Entity
from .registry import Registry
from .selector import Selector

ET = TypeVar("ET", bound="Entity")


class Record(HasContent, HasOrder, Entity):
    """Frozen ordered artifact with content identity and optional origin reference.

    Why
    ---
    Records capture immutable runtime facts that should compare by content and remain
    orderable for stream-like processing.

    Key Features
    ------------
    - **Three identity layers**: stable ``uid`` from :class:`Entity`, content equality
      from :class:`HasContent`, and sequence ordering from :class:`HasOrder`.
    - **Frozen + flexible schema**: ``frozen=True`` with ``extra='allow'`` supports
      arbitrary payload fields in derived record families.
    - **External origin dereference**: ``origin_id`` stores a producer reference, and
      :meth:`origin` resolves it through an explicitly supplied registry.

    Notes
    -----
    ``origin_id`` is not a registry-aware pointer. Dereference requires passing the
    correct lookup registry at call time.

    Example:
        >>> r = Record(content="foo")
        >>> r.get_hashable_content()
        'foo'
        >>> try:
        ...     r.content = "bar"
        ... except ValidationError as e:
        ...     print(e)  # doctest: +ELLIPSIS
        1 validation error ...
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)
    origin_id: Identifier = None

    def get_hashable_content(self) -> Any:
        for field_name in ["content", "payload", "data"]:
            if hasattr(self, field_name):
                return getattr(self, field_name)
        raise AttributeError("No content available.")

    # since a record is frozen, we _can_ cache the value hash minus non-generics
    # (uid, label) and use it as the content hash in a pinch.

    def origin(self, registry: Registry[ET]) -> ET:
        return registry.get(self.origin_id)


OrderedEntity = TypeVar("OrderedEntity", bound=Union[Entity, HasOrder])


class OrderedRegistry(Registry[OrderedEntity]):
    """Append-only ordered registry with sort-key range slicing.

    Why
    ---
    Ordered registries provide deterministic range queries over members with
    :meth:`sort_key` support while keeping the core primitive independent from
    higher-level stream marker/bookmark policies.

    Key Features
    ------------
    - append-only mutation model via :meth:`append`/:meth:`extend`;
    - generic key accessors :meth:`min_key` / :meth:`max_key`;
    - half-open range queries through :meth:`get_slice` with optional selector
      composition.

    Notes
    -----
    Named bookmarks/sections are intentionally out of scope for this core type and
    should be layered above it (for example in VM/story stream services).
    """

    def append(self, record: OrderedEntity) -> None:
        self.add(record)

    def extend(self, records: Iterable[OrderedEntity]) -> None:
        for record in records:
            self.append(record)

    def min_key(self, sort_key: Callable[[OrderedEntity], Any] | None = None) -> Any:
        if not self.members:
            return None
        key_fn = sort_key or (lambda member: member.sort_key())
        return min(key_fn(member) for member in self.members.values())

    def max_key(self, sort_key: Callable[[OrderedEntity], Any] | None = None) -> Any:
        if not self.members:
            return None
        key_fn = sort_key or (lambda member: member.sort_key())
        return max(key_fn(member) for member in self.members.values())

    def get_slice(
        self,
        start_key: Any = None,
        stop_key: Any = None,
        selector: Selector | None = None,
        sort_key: Callable[[OrderedEntity], Any] | None = None,
    ) -> Iterator[OrderedEntity]:
        """Yield members where ``start_key <= sort_key(member) < stop_key``.

        Bounds are half-open and optional. Passing ``None`` for either bound means
        unbounded in that direction.
        """

        key_fn = sort_key or (lambda member: member.sort_key())

        def in_range(member: OrderedEntity) -> bool:
            key = key_fn(member)
            if start_key is not None and key < start_key:
                return False
            if stop_key is not None and key >= stop_key:
                return False
            return True

        selector = selector or Selector()
        base_predicate = selector.predicate

        def combined_predicate(member: OrderedEntity) -> bool:
            if not in_range(member):
                return False
            if base_predicate is not None and not base_predicate(member):
                return False
            return True

        effective_selector = selector.with_criteria(predicate=combined_predicate)
        return self.find_all(effective_selector, sort_key=key_fn)

    def remove(self, *_args: Any, **_kwargs: Any) -> None:
        raise NotImplementedError("Cannot remove records from an OrderedRegistry.")
