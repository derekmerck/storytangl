from __future__ import annotations
from typing import Optional, Iterator, TypeVar, Generic, Type, Self, Any

from pydantic import Field

from tangl.type_hints import UnstructuredData, Identifier
from .entity import Entity
from .selector import Selector
from .registry import Registry
from .record import Record

# todo: round tripping script items -- payload.unstructure() -> yaml, add script-specific flags to fields to indicate author-facing.

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
    """

    # todo: should be unstructure=False, if we exclude it doesn't get used in eq
    payload: ET = Field(..., exclude=True)

    def get_content(self):
        return self.payload.unstructure()

    @classmethod
    def from_entity(cls, entity: Entity):
        return cls(payload=entity.evolve())

    @classmethod
    def from_data(cls, data: UnstructuredData, default_kind: Type[ET]=None) -> Self:
        if default_kind is not None:
            data.setdefault('kind', default_kind)
        entity = Entity.structure(data)
        return cls.from_entity(entity)

    restrictions: Any = None
    # By default, templates are generic archetypes and may be used without restriction.
    # In some cases, we want to impose other restrictions, for example, only allowing a template
    # to be used within a scope, or once per scope.

    # conflate/delegate identity matching
    def has_kind(self, kind: Type[Entity]) -> bool:
        return super().has_kind(kind) or self.payload.has_kind(kind)

    def has_tags(self, *tags) -> bool:
        return set(tags).issubset(self.tags.union(self.payload.tags))

    def get_identifiers(self) -> set[Identifier]:
        return super().get_identifiers().union( self.payload.get_identifiers() )

    # create copies
    def materialize(self, **updates) -> ET:
        if 'kind' in updates:
            if not issubclass(updates['kind'], self.payload.__class__):
                raise TypeError("If update includes kind, result will be a different class, suggested to only use when increasing specificity.")
        return self.payload.evolve(**updates)

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        # todo: could use field annotation introspection to discover members and payload include nested entities and automatically structure/unstructure them recursively
        data['payload'] = self.payload.unstructure()
        return data

    @classmethod
    def structure(cls, data: UnstructuredData) -> ET:
        data['payload'] = Entity.structure(data['payload'])
        return cls.structure(data)


class Snapshot(EntityTemplate):

    def materialize(self, **updates) -> ET:
        if updates:
            raise TypeError("Snapshot does not support updates")
        return super().materialize()


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
