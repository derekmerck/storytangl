# tangl/core/template.py
from __future__ import annotations

from typing import Optional, Iterator, TypeVar, Generic, Type, Self, Any
from uuid import uuid4
import logging

from pydantic import Field

from tangl.type_hints import UnstructuredData, Identifier
from .entity import Entity
from .selector import Selector
from .registry import Registry, HierarchicalGroup, RegistryAware
from .record import Record

logger = logging.getLogger(__name__)

ET = TypeVar("ET", bound=Entity)

NONGENERIC_FIELDS = {'uid', 'seq'}  # discarded when decompiling to script


class EntityTemplate(RegistryAware, Record, Generic[ET]):
    # language=markdown
    """
    Semi-structured data representation.

    Round-trip as a script item can use `templ_inst = compile(script_item)` or
    `script_item = templ_inst.decompile()`.

    ```
    Script ──compile─▶ Template ──materialize──▶ Live ◀──structure── Persistence
    (dict)             (record)                (entity)                 (dict)
      ▲                    │                       │                       ▲
      └─────decompile──────┘                       └──────unstructure──────┘
    ```

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
    # template to be used within a scope, or once per scope.  That should be captured in
    # metadata.

    payload: ET = Field(..., exclude=True)

    def get_label(self):
        return self.label or f"from-{self.payload.get_label()}"

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

    def has_template_kind(self, kind: Type[Entity]) -> bool:
        return super().has_kind(kind)

    def has_payload_kind(self, kind: Type[Entity]) -> bool:
        return self.payload.has_kind(kind)

    def has_tags(self, *tags) -> bool:
        return set(tags).issubset(self.tags.union(self.payload.tags))

    def get_identifiers(self) -> set[Identifier]:
        return super().get_identifiers().union(self.payload.get_identifiers())

    # create copies
    def materialize(self, preserve_uid: bool = False, **updates) -> ET:
        # if preserve_uid is true
        if 'kind' in updates:
            if not issubclass(updates['kind'], self.payload.__class__):
                raise TypeError(
                    "If update includes kind, result will be a different class, suggested to only use when increasing specificity."
                )
        if not preserve_uid:
            updates.setdefault('uid', uuid4())  # create a new uid if not provided
        else:
            updates.pop('uid', None)  # exact copy, discard any override uid
        return self.payload.evolve(**updates)

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        # TODO: could use field annotation introspection to discover members and
        #       payload include nested entities and automatically structure/unstructure
        #       them recursively
        data['payload'] = self.payload.unstructure()
        return data

    @classmethod
    def structure(cls, data: UnstructuredData, _ctx=None) -> Self:
        data = dict(data)
        data['payload'] = Entity.structure(data['payload'], _ctx=_ctx)
        return super().structure(data)

    def decompile(self, generify = True) -> UnstructuredData:
        # typically decompile will be used to go back to an author-facing
        # script format, so we want to generify the payload as much as
        # possible by removing irrelevant live instance fields.
        data = self.payload.unstructure()
        if generify:
            for f in NONGENERIC_FIELDS:
                data.pop(f, None)
            if data.get('kind', None) is Entity:
                # get rid of kind if it's redundant
                # we will track this more extensively with 'explicit_fields'
                # metadata during compile and defaults based on template subtypes
                data.pop('kind', None)
        return data

    @classmethod
    def compile(cls, data: UnstructuredData, _ctx=None) -> Self:
        # Convenience for `structure(payload=<unstructured entity>)`
        return cls.structure({'payload': data}, _ctx=_ctx)

class TemplateRegistry(Registry[EntityTemplate]):
    """A registry of templates.

    Example:
        >>> tr = TemplateRegistry()
        >>> tr.add(EntityTemplate.from_data({'label': 'abc'}))
        >>> tr.add(EntityTemplate.from_data({'label': 'def'}))
        >>> tr.materialize_one(Selector.from_identifier('abc'))
        <Entity:abc>
        >>> list(tr.materialize_all())
        [<Entity:abc>, <Entity:def>]
    """

    def materialize_one(self, selector: Selector = None, sort_key=None, update: dict = None) -> Optional[ET]:
        templ = self.find_one(selector=selector, sort_key=sort_key)
        if templ is not None:
            update = update or {}
            return templ.materialize(**update)

    def materialize_all(self, selector: Selector = None, sort_key=None) -> Iterator[ET]:
        # If you want to apply an update, do it one at a time.
        templs = self.find_all(selector=selector, sort_key=sort_key)
        return (templ.materialize() for templ in templs)

    @classmethod
    def compile(cls, data: list[UnstructuredData], _ctx=None, **kwargs) -> Self:
        # this is 'registry = compile(script)' when script is a list of top-level template groups.
        inst = cls(**kwargs)
        for item in data:
            item = dict(item)
            factory = TemplateGroup if 'members' in item else EntityTemplate
            template = factory.compile(data=item, _ctx=_ctx)
            if isinstance(template, Iterator):
                # Factory may yield multiple items.
                for t in template:
                    inst.add(t)
            else:
                inst.add(template)
        return inst

    def decompile_all(self, generify = True) -> list[UnstructuredData]:
        # this is 'script = decompile(registry)' when script is a list of top-level template groups
        data: list[UnstructuredData] = []

        top_level = self.find_all(Selector(
            has_template_kind=TemplateGroup,
            parent=None))
        for item in top_level:
            logger.debug(f"Decomposing tl item: {item!r} {item.parent!r}")
            data.append(item.decompile(generify=generify))
        return data


class TemplateGroup(EntityTemplate, HierarchicalGroup):
    """Enables templates to _un/structure_ with inline children for hierarchical scripts.

    They are registry aware and must be part of a template registry.

    Children/members are used as scope-hints but stored independently.
    Parent template identifiers are used to recreate hierarchical scripts that have
    been decomposed into independent templates in a registry.

    Consider there are two forms of template-ir:
    - "tree-ir", which is near-native format for template payloads with scope
      and grouping represented by inlining templates within templates.
    - "flat-ir", which is how templates wrapping a validated payload are stored
      independently in a flat but searchable registry.

    There is exactly 1 flat-ir representation for a given configuration, but there
    are many possible tree-ir representations for the same, depending on how grouping
    is used. So we will need additional parsing and annotations for which items are
    gathered into which groups in order to 'round-trip' tree-ir.

    For script-ir groups that have members split across multiple fields, the field name
    is usually the kind hint, i.e., Scenes: [ ... ]. For groups where members are in
    a dictionary, the key is usually the label. i.e., Scenes: { scene1: ... , scene2: ... }

    Example (tree-ir ⇄ flat registry round-trip):
        >>> # Tree-IR payload (human-authored script shape)
        >>> script = [
        ...   { 'label': 'chapter-1',
        ...     'members': [
        ...       { 'label': 'scene-1.1',
        ...         'members': [
        ...           {'label': 'block-1.1.1'},
        ...           {'label': 'block-1.1.2'} ]},
        ...       { 'label': 'scene-1.2',
        ...         'members': [ {'label': 'block-1.2.1'} ] } ] } ]
        >>> tr = TemplateRegistry.compile(script)
        >>> len(tr)  # 1 ch, 2 sc, 3 bl = 6
        6
        >>> # Decompile back to a nested tree-ir payload.
        >>> roundtrip = tr.decompile_all()
        >>> script == roundtrip
        True
    """

    member_defaults: dict[str, Any] = Field(default_factory=dict)
    # capture things like default-kind for members is "Scene" or scope is "parent-path.*"
    # inject member defaults into members when structuring from payload, and exclude
    # matching values from members when they are unstructured as payloads.

    @classmethod
    def compile(cls, data: UnstructuredData, _ctx=None) -> Iterator[EntityTemplate]:
        """Flatten a tree-ir payload into flat templates.

        This yields templates in *depth-first* order (children first), while still
        recording *direct* children for each group via `member_ids`.

        Implementation trick: use a nested generator that `return`s the uid of the
        direct root template for a payload subtree. Parent calls `child_id = yield from ...`.
        """

        def _flatten(subtree: UnstructuredData) -> Iterator[EntityTemplate]:
            subtree = dict(subtree)
            members = subtree.pop('members', None)

            # If this node has members, it is a TemplateGroup.
            if members is not None:
                member_ids: list[Any] = []
                for child in members or []:
                    child_id = yield from _flatten(child)
                    member_ids.append(child_id)

                # IMPORTANT: `member_ids` belong to the TemplateGroup record (HierarchicalGroup),
                # not the payload. Payload stays "near-native".
                group = cls.structure({'payload': subtree, 'member_ids': member_ids}, _ctx=_ctx)
                yield group
                return group.uid

            # Otherwise this node is a plain EntityTemplate.
            templ = EntityTemplate.structure({'payload': subtree}, _ctx=_ctx)
            yield templ
            return templ.uid

        # Delegate to the nested generator.
        yield from _flatten(data)

    def decompile(self, generify: bool = True) -> UnstructuredData:
        data = super().decompile(generify=generify)
        data['members'] = []
        for member in self.members():
            data['members'].append(member.decompile(generify=generify))
        return data


class Snapshot(EntityTemplate):
    """Snapshot is a variant of a template that wraps an existing entity and allows it
    to be recreated later, but disallows any modification at materialization time.

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
