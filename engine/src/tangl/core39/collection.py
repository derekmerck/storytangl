from __future__ import annotations
from uuid import UUID
from typing import TypeVar, Iterator, Generic, Optional
from itertools import chain

from pydantic import Field, PrivateAttr

from .entity import Entity, Structurable
from .selection import Selector

##############################
# COLLECTIONS
##############################

class RegistryAware(Entity, Structurable):
    registry: Registry = PrivateAttr(None)  # be careful that this is NOT copied or serialized

    def find_groups(self, s: Selector = None, **criteria) -> Iterator[EntityGroup]:
        criteria = criteria or {}
        criteria['has_member'] = self
        if s is None:
            s = Selector(**criteria)
        elif criteria:
            s.update(**criteria)
        return self.registry.find_all(s)


ET = TypeVar("ET", bound=RegistryAware)

class Registry(Entity, Structurable, Generic[ET]):
    # serializable collection
    members: dict[UUID, ET] = Field(default_factory=dict)

    def get(self, key: UUID) -> ET:
        return self.members.get(key)

    def add(self, item: ET) -> None:
        self.members[item.uid] = item
        if isinstance(item, RegistryAware):
            item.registry = self

    def find_all(self, s: Selector = None, sort_key = None, **criteria) -> Iterator[ET]:
        return self.chain_find_all(self, s=s, sort_key=sort_key, **criteria)

    def find_one(self, s: Selector = None, **criteria) -> Optional[ET]:
        return next(self.find_all(s, **criteria), None)

    @classmethod
    def chain_find_all(cls, *registries, s: Selector = None, sort_key = None, **criteria) -> Iterator[ET]:
        if s is None:
            s = Selector(**criteria)
        elif criteria is not None:
            s.update(**criteria)
        selected = s.select_all(chain.from_iterable(r.members.values() for r in registries))
        if sort_key is not None:
            yield from sorted(selected, key=sort_key)
        else:
            yield from selected

    def find_groups(self, s: Selector = None, **criteria) -> Iterator[EntityGroup]:
        criteria = criteria or {}
        criteria['has_kind'] = EntityGroup
        return self.find_all(s=s, **criteria)


class EntityGroup(RegistryAware):
    # group of registry-aware entities
    member_ids: list[UUID] = Field(default_factory=list)

    @property
    def members(self) -> list[RegistryAware]:
        return [self.registry.get(member_id) for member_id in self.member_ids]

    def add_member(self, member: RegistryAware):
        if member.uid not in self.member_ids:
            self.member_ids.append(member.uid)

    def remove_member(self, member: RegistryAware):
        if member.uid in self.member_ids:
            self.member_ids.remove(member.uid)

    def has_member(self, member: Entity) -> bool:
        return member.uid in self.member_ids
