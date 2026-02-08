# tangl/core/template.py
from __future__ import annotations
from typing import Optional, Iterator, TypeVar, Generic, Type, Self
from uuid import uuid4

from pydantic import Field

from tangl.type_hints import UnstructuredData, Identifier
from .entity import Entity
from .selector import Selector
from .registry import Registry
from .record import Record

# todo: round tripping script items -- payload.unstructure() -> yaml, add
#       script-specific flags to fields to indicate author-facing.

ET = TypeVar("ET", bound=Entity)

class EntityTemplate(Record, Generic[ET]):
    """
    Semi-structured data representation.

    Example:
        >>> class PseudoEntity(Entity): ...
        >>> data = {'label': 'abc'}
        >>> templ = EntityTemplate.from_data(data, default_kind=PseudoEntity)
        >>> templ.has_kind(EntityTemplate) and templ.has_kind(PseudoEntity)
        True
        >>> templ.materialize()
        <PseudoEntity:abc>
        >>> class PseudoEntity2(PseudoEntity): ...
        >>> templ.materialize(kind=PseudoEntity2, label="def")
        <PseudoEntity2:def>
        >>> templ.materialize().uid != templ.payload.uid  # created with fresh id
        True
    """
    # By default, templates are generic archetypes and may be used without restriction.
    # In some cases, we want to impose other restrictions, for example, only allowing a
    # template to be used within a scope, or once per scope.  that should be captured in
    # metadata

    # todo: should be unstructure=False, if we exclude it doesn't get used in eq
    payload: ET = Field(..., exclude=True)

    def get_hashable_content(self):
        return self.payload.unstructure()

    @classmethod
    def from_entity(cls, entity: Entity):
        return cls(payload=entity.evolve())  # holds a clean, deep copy

    @classmethod
    def from_data(cls, data: UnstructuredData, default_kind: Type[ET] = None) -> Self:
        if default_kind is not None:
            data.setdefault('kind', default_kind)
        entity = Entity.structure(data)
        return cls.from_entity(entity)

    # conflate/delegate identity matching
    def has_kind(self, kind: Type[Entity]) -> bool:
        return super().has_kind(kind) or self.payload.has_kind(kind)

    def has_tags(self, *tags) -> bool:
        return set(tags).issubset(self.tags.union(self.payload.tags))

    def get_identifiers(self) -> set[Identifier]:
        return super().get_identifiers().union( self.payload.get_identifiers() )

    # create copies
    def materialize(self, preserve_uid=False, **updates) -> ET:
        # if preserve_uid is true
        if 'kind' in updates:
            if not issubclass(updates['kind'], self.payload.__class__):
                raise TypeError("If update includes kind, result will be a different class, suggested to only use when increasing specificity.")
        if not preserve_uid:
            updates.setdefault('uid', uuid4())  # create a new uid if not provided
        else:
            updates.pop('uid', None)  # exact copy, discard any override uid
        return self.payload.evolve(**updates)

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        # todo: could use field annotation introspection to discover members and
        #       payload include nested entities and automatically structure/unstructure
        #       them recursively
        data['payload'] = self.payload.unstructure()
        return data

    @classmethod
    def structure(cls, data: UnstructuredData) -> ET:
        data['payload'] = Entity.structure(data['payload'])
        return super().structure(data)


class Snapshot(EntityTemplate):
    """
    Example:
        >>> e = Entity(label='abc')
        >>> s = Snapshot.from_entity(e)
        >>> ee = s.materialize()
        >>> e is not ee and e == ee  # preserves uid
        True
    """

    def materialize(self, preserve_uid: bool = True, **updates) -> ET:
        if updates:
            raise TypeError("Snapshot does not support updates")
        if not preserve_uid:
            raise TypeError("Snapshot does not support preserve_uid != True")
        return super().materialize(preserve_uid=True)


class TemplateRegistry(Registry[EntityTemplate]):
    """
    Example:
        >>> tr = TemplateRegistry()
        >>> tr.add(EntityTemplate.from_data({'label': 'abc'}))
        >>> tr.add(EntityTemplate.from_data({'label': 'def'}))
        >>> tr.materialize_one(Selector.from_identifier('abc'))
        <Entity:abc>
        >>> list(tr.materialize_all())
        [<Entity:abc>, <Entity:def>]
    """

    def materialize_one(self, selector: Selector = None, sort_key = None, update: dict = None) -> Optional[ET]:
        templ = self.find_one(selector=selector, sort_key=sort_key)
        if templ is not None:
            update = update or {}
            return templ.materialize(**update)

    def materialize_all(self, selector: Selector = None, sort_key = None) -> Iterator[ET]:
        # If you want to apply an update, do it one at a time.
        templs = self.find_all(selector=selector, sort_key=sort_key)
        return (templ.materialize() for templ in templs)
