from __future__ import annotations
from typing import Type, TypeAlias, Self, TYPE_CHECKING
from pydantic import Field
from uuid import uuid4

from tangl.type_hints import Hash, StringMap
from .entity import Entity, Structurable
from .collection import Registry, RegistryAware
from .record import Record

if TYPE_CHECKING:
    from .graph import Graph


##############################
# FACTORY
##############################

Kind: TypeAlias = Type[Entity]

class Template(Record, RegistryAware):
    templ: Entity

    def has_kind(self, kind: Kind) -> bool:
        return super().has_kind(kind) or self.templ.has_kind(kind)

    def materialize(self, preserve_uid=False, **updates) -> Kind:
        if not preserve_uid:
            updates["uid"] = uuid4()
        inst = self.templ.clone(**updates)
        return inst


class Factory(Registry[Template]):

    def materialize_all(self) -> 'Graph':
        from .graph import Graph
        g = Graph()
        for v in self.members.values():
            for item in v.materialize_all():  # should bring choice edges into existence
                g.add(item)

        # have to do this top-down or bottom up
        for s in g.get_subgraphs():
            members = g.find_all(exact_scope=s.position)
            for m in members:
                s.add_member(m)

        for e in g.get_edges():
            pred = g.find_one(name=e.pred_id)
            succ = g.find_one(name=e.pred_id)
            e.predecessor = pred
            e.successor = succ

        return g



##############################
# ENTITY SNAPSHOT
##############################

class Snapshot(Template):

    def materialize(self, **updates):
        return super().materialize(preserve_uid=True, **updates)


##############################
# ENTITY DELTA
##############################

# snapshot + deltas = reconstructed state

class EntityDelta(Record):
    diff: StringMap = Field(default_factory=dict)
    base_hash: Hash = None
    final_hash: Hash = None

    @classmethod
    def _validate_state_hash(cls, entity: Structurable, check_hash: Hash) -> None:
        if check_hash is None:
            raise ValueError("Req strict deltas, but no check_hash provided")
        state_hash = entity.state_hash()
        if check_hash != state_hash:
            raise ValueError("Invalid state hash")

    def apply(self, entity: Structurable, strict: bool = True) -> None:
        if strict:
            self._validate_state_hash(entity, check_hash=self.base_hash)
        entity.evolve(updates=self.updates)
        if strict:
            self._validate_state_hash(entity, check_hash=self.final_hash)

    @classmethod
    def from_entity_diff(cls, base: Structurable, final: Structurable) -> Self:
        if not getattr(final, "_maybe_updated", True):
            # set flag for maybe updated
            return None
        diff = base - final
        if not diff:
            return None
        return cls(
            origin = base.uid,
            diff = diff,
            initial_hash = base.state_hash(),
            final_hash = final.state_hash(),
        )

class RegistryDelta(EntityDelta):
    # similar to how registries unstructure and restructure
    member_diffs: list[EntityDelta] = Field(default_factory=list)

    def apply(self, registry: Registry, strict: bool = True):
        super().apply(registry, strict=strict)
        for entity_delta in self.member_updates:
            entity = registry.get(entity_delta.entity_id)
            entity_delta.apply(entity, strict=strict)

    @classmethod
    def from_registry_diff(cls, registry: Registry, strict: bool = True):
        ...

