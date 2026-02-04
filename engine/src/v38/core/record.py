from typing import ClassVar, TypeVar, Union, TypeAlias

from pydantic import Field, ConfigDict

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
    """
    config: ClassVar[ConfigDict] = ConfigDict(extra="allow", frozen=True)
    origin_id: Identifier = None

    def origin(self, registry: Registry[ET]) -> ET:
        return registry.get(self.origin_id)

OrderedEntity = TypeVar("OrderedEntity", bound=Union[Entity, HasOrder])

class OrderedRegistry(Registry[OrderedEntity]):

    bookmarks: dict[str, list[int]] = Field(default_factory=dict)

    def max_seq(self) -> int:
        return max([v.seq for v in self.members.values()]) or 0

    def set_bookmark(self, channel: str = "_"):
        if channel not in self.bookmarks:
            self.bookmarks[channel] = []
        self.bookmarks[channel].append(self.max_seq())

    def slice(self, start=0, stop=-1, channel: str = "_") -> OrderedEntity:
        bookmarks = self.bookmarks[channel]
        seq_start = bookmarks[start]
        seq_stop = bookmarks[stop]
        selector = Selector(attributes={'seq': (seq_start, seq_stop)})
        return self.find_all(selector, sort_key=lambda v: v.sort_key())

