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
        """Return the primary content field used for content hashing.

        Resolution order is ``content`` then ``payload`` then ``data``.
        """
        for field_name in ["content", "payload", "data"]:
            if hasattr(self, field_name):
                return getattr(self, field_name)
        raise AttributeError("No content available.")

    # since a record is frozen, we _can_ cache the value hash minus non-generics
    # (uid, label) and use it as the content hash in a pinch.

    def origin(self, registry: Registry[ET]) -> ET:
        """Resolve ``origin_id`` through an explicit registry."""
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
    should be layered above it (for example in VM/story stream services). Core
    keeps append/slice only; bookmark channels and destructive undo truncation are
    runtime-policy concerns.
    """

    markers: dict[str, dict[str, int]] = Field(default_factory=dict)

    @property
    def data(self) -> dict[Any, OrderedEntity]:
        """Legacy alias for ``members``."""
        return self.members

    @data.setter
    def data(self, value: dict[Any, OrderedEntity]) -> None:
        self.members = value

    def append(self, record: OrderedEntity) -> None:
        """Append one ordered entity to the registry."""
        self.add(record)

    def extend(self, records: Iterable[OrderedEntity]) -> None:
        """Append many ordered entities in input order."""
        for record in records:
            self.append(record)

    def min_key(self, sort_key: Callable[[OrderedEntity], Any] | None = None) -> Any:
        """Return minimum member sort key, or ``None`` for an empty registry."""
        if not self.members:
            return None
        key_fn = sort_key or (lambda member: member.sort_key())
        return min(key_fn(member) for member in self.members.values())

    def max_key(self, sort_key: Callable[[OrderedEntity], Any] | None = None) -> Any:
        """Return maximum member sort key, or ``None`` for an empty registry."""
        if not self.members:
            return None
        key_fn = sort_key or (lambda member: member.sort_key())
        return max(key_fn(member) for member in self.members.values())

    @property
    def max_seq(self) -> int:
        """Legacy compatibility alias for highest observed ``seq``."""
        if not self.members:
            return -1
        values: list[int] = []
        for member in self.members.values():
            seq = getattr(member, "seq", -1)
            try:
                values.append(int(seq))
            except (TypeError, ValueError):
                values.append(-1)
        return max(values, default=-1)

    def add_record(self, record: OrderedEntity) -> None:
        """Legacy compatibility helper used by stream-oriented call sites."""
        self.append(record)

    def last(self, **criteria: Any) -> OrderedEntity | None:
        """Return the last matching item by ``seq``."""
        results = list(self.find_all(**criteria))
        if not results:
            return None
        return max(results, key=lambda item: int(getattr(item, "seq", -1)))

    def get_slice(
        self,
        start_key: Any = None,
        stop_key: Any = None,
        selector: Selector | None = None,
        sort_key: Callable[[OrderedEntity], Any] | None = None,
        *,
        start_seq: Any = None,
        end_seq: Any = None,
        predicate: Callable[[OrderedEntity], bool] | None = None,
        **criteria: Any,
    ) -> Iterator[OrderedEntity]:
        """Yield members where ``start_key <= sort_key(member) < stop_key``.

        Bounds are half-open and optional. Passing ``None`` for either bound means
        unbounded in that direction.
        """
        if start_seq is not None:
            start_key = start_seq
        if end_seq is not None:
            stop_key = end_seq

        key_fn = sort_key or (lambda member: member.sort_key())

        def in_range(member: OrderedEntity) -> bool:
            key = key_fn(member)
            if start_key is not None and key < start_key:
                return False
            if stop_key is not None and key >= stop_key:
                return False
            return True

        selector = self._normalize_selector(selector, **criteria) or Selector()
        base_predicate = selector.predicate

        def combined_predicate(member: OrderedEntity) -> bool:
            if not in_range(member):
                return False
            if base_predicate is not None and not base_predicate(member):
                return False
            if predicate is not None and not predicate(member):
                return False
            return True

        effective_selector = selector.with_criteria(predicate=combined_predicate)
        return self.find_all(effective_selector, sort_key=key_fn)

    def set_marker(
        self,
        marker_name: str,
        marker_type: str = "_",
        marker_seq: int | None = None,
        *,
        overwrite: bool = False,
    ) -> None:
        """Set/update a named stream marker (legacy compatibility)."""
        marker_seq = self.max_seq + 1 if marker_seq is None else marker_seq
        marker_bucket = self.markers.setdefault(marker_type, {})
        if not overwrite and marker_name in marker_bucket:
            raise KeyError(f"Marker {marker_name} already exists")
        marker_bucket[marker_name] = marker_seq

    def _next_marker_seq(self, start_seq: int, marker_type: str = "_") -> int:
        """Return next marker seq of same type, or stream end."""
        marker_bucket = self.markers.get(marker_type, {})
        if not marker_bucket:
            return self.max_seq + 1
        next_seqs = sorted(seq for seq in marker_bucket.values() if seq > start_seq)
        return next_seqs[0] if next_seqs else self.max_seq + 1

    def get_section(
        self,
        marker_name: str,
        marker_type: str = "_",
        **criteria: Any,
    ) -> Iterator[OrderedEntity]:
        """Yield records in [marker, next-marker) for a marker namespace."""
        marker_bucket = self.markers.get(marker_type) or {}
        if not marker_bucket:
            raise KeyError(f"{marker_name}@{marker_type} not found")

        if marker_name == "latest":
            _, start_seq = max(marker_bucket.items(), key=lambda item: item[1])
        else:
            if marker_name not in marker_bucket:
                raise KeyError(f"{marker_name}@{marker_type} not found")
            start_seq = marker_bucket[marker_name]

        end_seq = self._next_marker_seq(start_seq, marker_type)
        return self.get_slice(start_seq=start_seq, end_seq=end_seq, **criteria)

    def remove(self, *_args: Any, **_kwargs: Any) -> None:
        """Disallow removal to preserve append-only history semantics."""
        raise NotImplementedError("Cannot remove records from an OrderedRegistry.")
