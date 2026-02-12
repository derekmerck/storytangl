# tangl/core/record.py
from __future__ import annotations
from typing import ClassVar, TypeVar, Union, Iterable

from pydantic import Field, ConfigDict, ValidationError

from tangl.type_hints import Identifier
from .bases import HasContent, HasOrder
from .entity import Entity
from .registry import Registry
from .selector import Selector

ET = TypeVar('ET', bound='Entity')


class Record(HasContent, HasOrder, Entity):
    """
    Frozen entity with content identity, ordering, and reference their
    origin by id.

    Guarantees:
    - Immutable after creation
    - Content-based equality
    - Deterministic ordering via seq
    - Records should never have registry/graph dependencies, so dereferencing
      the origin requires passing the correct lookup index.

    Example:
        >>> r = Record(content='foo')
        >>> r.get_hashable_content()
        'foo'
        >>> try:
        ...     r.content = 'bar'
        ... except ValidationError as e:
        ...     print(e)  # doctest: +ELLIPSIS
        1 validation error ...
    """
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)
    origin_id: Identifier = None

    def get_hashable_content(self):
        for field_name in ['content', 'payload', 'data']:
            if hasattr(self, field_name):
                return getattr(self, field_name)
        raise AttributeError("No content available.")

    def origin(self, registry: Registry[ET]) -> ET:
        return registry.get(self.origin_id)

OrderedEntity = TypeVar("OrderedEntity", bound=Union[Entity, HasOrder])

class OrderedRegistry(Registry[OrderedEntity]):
    """Ordered registries may be sliced and bookmarked by channel"""

    bookmarks: dict[str, list[int]] = Field(default_factory=dict)

    def append(self, record: OrderedEntity):
        # actually want to verify this _sorts_ last, like sort_key is biggest
        # if not record > self.max_seq():
        #     raise IndexError("Record out of sequence for append")
        self.add(record)

    def extend(self, records: Iterable[OrderedEntity]):
        for record in records:
            self.append(record)

    def max_seq(self) -> int:
        return max([v.seq for v in self.members.values()]) or 0

    def set_bookmark(self, channel: str = "_"):
        if channel not in self.bookmarks:
            self.bookmarks[channel] = []
        self.bookmarks[channel].append(self.max_seq())

    def slice(self, start=0, stop=-1, channel: str = "_",
              selector: Selector = Selector()) -> OrderedEntity:
        bookmarks = self.bookmarks[channel]
        seq_start = bookmarks[start]
        seq_stop = bookmarks[stop]
        selector = selector.with_criteria(has_seq_in=(seq_start, seq_stop), channel=channel)
        return self.find_all(selector, sort_key=lambda v: v.sort_key())
