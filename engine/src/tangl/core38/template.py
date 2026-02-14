# tangl/core/template.py
# language=markdown
"""Templates (v38): compile/decompile and materialization.

This module defines the authoring boundary for core templates and separates
compile/decompile from runtime materialization.

See Also
--------
:class:`tangl.core38.record.Record`
    Template records inherit frozen/content/seq behavior from ``Record``.
:mod:`tangl.core38.registry`
    Registry-aware and hierarchical behaviors used by template containers.

Notes
-----
``NONGENERIC_FIELDS`` defines runtime-only fields stripped by ``decompile()``.
"""
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
    """Template wrapper around an entity payload.

    An `EntityTemplate` stores a prototype entity (`payload`) and provides three distinct
    operations:

    - **compile**: `dict → EntityTemplate` (authoring loop)
    - **decompile**: `EntityTemplate → dict` (authoring loop)
    - **materialize**: `EntityTemplate → Entity` (runtime entry)

    ### What a template is (and is not)

    - A template is **not** a live entity in the runtime graph.
    - A template may be stored in a `TemplateRegistry` and searched using `Selector`.
    - Templates can participate in hierarchy/grouping when combined with
      `TemplateGroup` (see below).

    ### Matching axes (important)

    Templates expose two independent matching axes:

    - **template-kind**: what wrapper record the template is (`EntityTemplate`, `Snapshot`, `TemplateGroup`)
    - **payload-kind**: what entity kind the template would materialize (`Scene`, `Block`, `Entity`, ...)

    Use `has_template_kind()` and `has_payload_kind()` to avoid ambiguity. The convenience
    method `has_kind()` matches either axis.

    ### Authoring vs persistence

    - `compile()` / `decompile()` are for author scripts and strip framework noise by policy.
    - `structure()` / `unstructure()` serialize the template record itself (including payload)
      and are appropriate for caching/transport of templates, not authoring.

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
        >>> templ.has_template_kind(EntityTemplate) and templ.has_payload_kind(PseudoEntity)
        True
        >>> templ.materialize()
        <PseudoEntity:abc>
        >>> class PseudoEntity2(PseudoEntity): ...
        >>> templ.materialize(kind=PseudoEntity2, label="def")
        <PseudoEntity2:def>
        >>> templ.materialize().uid != templ.payload.uid  # fresh id by default
        True
    """

    # By default, templates are generic archetypes and may be used without restriction.
    # In some cases, we want to impose other restrictions, for example, only allowing a
    # template to be used within a scope, or once per scope.  That should be captured in
    # metadata.

    payload: ET = Field(..., exclude=True)
    # Excluded from pydantic model_dump; unstructure/structure handles payload explicitly.

    def get_label(self):
        return self.label or f"from-{self.payload.get_label()}"

    def get_hashable_content(self):
        return self.payload.unstructure()

    @classmethod
    def from_entity(cls, entity: Entity):
        return cls(payload=entity.evolve())  # holds a clean, deep copy

    @classmethod
    def from_data(cls, data: UnstructuredData, default_kind: Type[ET] = None) -> Self:
        payload_data = dict(data)
        if default_kind is not None:
            payload_data.setdefault('kind', default_kind)
        entity = Entity.structure(payload_data)
        return cls.from_entity(entity)

    # conflate/delegate identity matching
    def has_kind(self, kind: Type[Entity]) -> bool:
        return super().has_kind(kind) or self.payload.has_kind(kind)

    def has_template_kind(self, kind: Type[Entity]) -> bool:
        return super().has_kind(kind)

    def has_payload_kind(self, kind: Type[Entity]) -> bool:
        return self.payload.has_kind(kind)

    def has_tags(self, *tags) -> bool:
        if len(tags) == 0:
            return True
        if len(tags) == 1 and tags[0] is None:
            return True
        if len(tags) == 1 and isinstance(tags[0], (tuple, list, set)):
            tags = tuple(tags[0])
        return set(tags).issubset(self.tags.union(self.payload.tags))

    def get_identifiers(self) -> set[Identifier]:
        return super().get_identifiers().union(self.payload.get_identifiers())

    # create copies
    def materialize(self, preserve_uid: bool = False, **updates) -> ET:
        # if preserve_uid is true
        if 'kind' in updates:
            if not issubclass(updates['kind'], self.payload.__class__):
                raise TypeError(
                    "materialize kind must be a subclass of payload kind "
                    f"{self.payload.__class__.__name__}, got {updates['kind'].__name__}"
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
    """Registry of templates with convenience materialization and authoring helpers.

    `TemplateRegistry` is the primary container for authoring-loop operations:

    - `compile(script)` builds a flat registry from a list of script dicts.
    - `decompile_all()` emits a list of script dicts from top-level template groups.

    Materialization helpers (`materialize_one`, `materialize_all`) provide a simple bridge
    into runtime, but they are not required for linting/compile/decompile.

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
    """Template + hierarchical group membership for script-shaped trees.

    A `TemplateGroup` is both:

    - an `EntityTemplate` wrapping a payload (the group node), and
    - a `HierarchicalGroup` whose membership is stored as `member_ids: list[UUID]`.

    This enables *tree-shaped* scripts to be compiled into a flat registry and later
    reconstructed.

    ## Representations

    - **tree-IR**: author-facing dicts with inline `members`.
    - **flat registry**: independent templates stored in a `TemplateRegistry`.

    `TemplateGroup.compile()` performs the tree-IR → flat registry conversion:

    - yields templates in **depth-first** order (children first)
    - records **direct** children for each group via `member_ids`

    `TemplateGroup.decompile()` performs the inverse projection:

    - emits the group payload as a script dict
    - recursively decompiles children into inline `members`

    Note: multiple tree-IR shapes can map to the same flat registry unless additional
    annotations are provided (e.g., kind-hints on member fields). v38 keeps the core
    mechanism minimal; higher layers may add richer script parsing.

    Example (tree-IR ⇄ flat registry round-trip):
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
        >>> len(tr)
        6
        >>> roundtrip = tr.decompile_all()
        >>> assert script == roundtrip
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
    """Persistence convenience: a template that recreates an entity exactly.

    A `Snapshot` is **not** part of the authoring loop. It is a persistence helper that
    reuses the template/materialization machinery to recreate a live entity with the same
    identifier and state.

    - `materialize()` preserves uid and rejects updates.
    - `decompile()` is not typically meaningful for snapshots.

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
