
from __future__ import annotations
from typing import Iterator, TypeVar, Generic
from uuid import UUID

from pydantic import ConfigDict

from .entity import Entity, HasContent, Structurable, HasOrder
from .collection import Registry
from .selection import Selector

##############################
# ARTIFACT
##############################

# See also:
#   - factory.Template, factory.Snapshot
#   - behavior.CallReceipt
#   - delta.EntityDelta, RegistryDelta

class Record(Entity, HasContent, HasOrder, Structurable):
    # Not generically "registry aware", so they can't reference one another directly
    model_config = ConfigDict(frozen=True)
    origin: Entity = None


class OrderedRegistry(Registry[Record]):

    members: dict[UUID, Record]

    def find_all(self, s: Selector = None, in_range: tuple[Record, Record] = None, **_) -> Iterator[RT]:
        ...
