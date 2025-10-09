from __future__ import annotations
from uuid import UUID, uuid4
from typing import Optional, Self, Iterator, Type, Callable, Iterable, TypeAlias, TypeVar
import logging
from copy import copy

from pydantic import BaseModel, Field, field_validator
import shortuuid

from tangl.type_hints import StringMap, Tag, Predicate, Identifier
from tangl.utils.hashing import hashing_func
from tangl.utils.base_model_plus import BaseModelPlus
from tangl.utils.sanitize_str import sanitise_str

logger = logging.getLogger(__name__)
match_logger = logging.getLogger(__name__ + '.match')
match_logger.setLevel(logging.WARNING)

def is_identifier(func: Callable) -> Callable:
    """Label Entity and subclass methods as providing an identifier."""
    setattr(func, '_is_identifier', True)
    return func

class Entity(BaseModelPlus):
    """
    Entity(label: str, tags: set[str])

    Base class for all managed objects in a narrative graph.

    Why
    ----
    Entities abstract identity and comparability across the system. They provide
    uniform identifiers, search predicates, and serialization. Everything else
    (graphs, records, handlers) builds on this.

    Key Features
    ------------
    * **Identifiers** – Each entity has a UUID plus optional label and tags.
      Identifiers can be discovered via :meth:`get_identifiers` and matched with
      :meth:`matches(has_identifier='foo')<matches>`.
    * **Serialization** – :meth:`structure` and :meth:`unstructure` provide
      round-trip conversion between entities and dict data.
    * **Audit tracking** – :attr:`is_dirty` flags non-reproducible mutations
      for replay validation.
    * **Search** – Entities can be filtered by arbitrary attribute criteria
      (e.g. :meth:`registry.find_all(label="scene1", has_tags={"npc"})<Registry.find_all>`).

    API
    ---
    - :meth:`matches(**criteria)<matches>` – test entity against criteria
    - :meth:`get_identifiers` – collect all identifiers
    - :meth:`has_tags` – membership test for tags
    - :meth:`structure` / :meth:`unstructure` – (de)serialization

    See also
    --------
    :class:`~tangl.core.entity.Selectable`
    :class:`~tangl.core.entity.Conditional`
    """
    uid: UUID = Field(default_factory=uuid4, json_schema_extra={'is_identifier': True})
    label: Optional[str] = Field(None, json_schema_extra={'is_identifier': True})
    tags: set[Tag] = Field(default_factory=set)
    # tag syntax can be used by the _parser_ as sugar for various attributes
    # - indicate domain memberships       domain
    # - automatically set default values  .str=100
    # - indicate relationships            @other_node.friendship=+10

    @field_validator('label', mode="after")
    @classmethod
    def _sanitize_label(cls, value):
        if isinstance(value, str):
            value = sanitise_str(value)
        return value

    @is_identifier
    def get_label(self) -> str:
        return self.label or self.short_uid()

    def matches(self, *, predicate: MatchPredicate = None, **criteria) -> bool:
        # Callable predicate funcs on self were passed
        if predicate is not None and not predicate(self):
            return False
        for k, v in criteria.items():
            # Sugar to test individual attributes
            if not hasattr(self, k):
                match_logger.debug(f'False: entity {self!r} has no attribute {k}')
                # Doesn't exist
                return False
            item = getattr(self, k)
            if (k.startswith("has_") or k.startswith("is_")) and callable(item):
                if not item(v):
                    # Is it a predicate attrib that returns false, like `has_tags={a,b,c}`?
                    match_logger.debug(f'False: entity {self!r}.{k}({v}) is False')
                    return False
                match_logger.debug(f'True: entity {self!r}.{k}({v}) is True')
            elif item != v:
                match_logger.debug(f'False: entity {self!r}.{k} != {v}')
                # Is it a straight comparison and not equal?
                return False
        return True

    @classmethod
    def filter_by_criteria(cls, values: Iterable[EntityT], **criteria) -> Iterator[EntityT]:
        return filter(lambda x: x.matches(**criteria), values)

    # Any `has_` methods should not have side effects as they may be called through **criteria args

    def get_identifiers(self) -> set[Identifier]:
        result = set()
        for f in self._fields(is_identifier=(True, False)):
            value = getattr(self, f)
            if value is not None:
                if isinstance(value, set):
                    result.update(value)
                else:
                    result.add(value)
        for cls in self.__class__.__mro__:
            for ff in cls.__dict__.values():
                if callable(ff) and getattr(ff, '_is_identifier', False):
                    value = ff(self)
                    if value is not None:
                        if isinstance(value, set):
                            result.update(value)
                        else:
                            result.add(value)
        return result

    def has_identifier(self, alias: Identifier) -> bool:
        return alias in self.get_identifiers()

    has_alias = has_identifier

    def has_tags(self, *tags: Tag) -> bool:
        # Normalize args to set[Tag]
        if len(tags) == 1 and isinstance(tags[0], set):
            tags = tags[0]  # already a set of tags
        else:
            tags = set(tags)
        match_logger.debug(f"Comparing query tags {tags} against {self.tags}")
        return tags.issubset(self.tags)

    def is_instance(self, obj_cls: Type[Self]) -> bool:
        # helper func for matches
        return isinstance(self, obj_cls)

    @is_identifier
    def short_uid(self) -> str:
        return shortuuid.encode(self.uid)

    is_dirty_: bool = Field(
        default=False,
        alias="is_dirty",
        json_schema_extra={"doc_private": True},
    )  #: :meta private:
    # audit indicator that the entity has been tampered with, invalidates certain debugging

    @property
    def is_dirty(self) -> bool:
        return self.is_dirty_

    def mark_dirty(self, reason: str | None = None) -> None:
        """Mark this entity as tainted by non-reproducible mutation."""
        object.__setattr__(self, "is_dirty_", True)
        if reason:
            logger.warning("%r marked dirty: %s", self, reason)

    def __repr__(self) -> str:
        s = self.get_label()
        return f"<{self.__class__.__name__}:{s}>"

    @is_identifier
    def _id_hash(self) -> bytes:
        # For persistent id's, use either the uid or a field annotated as UniqueLabel
        return hashing_func(self.uid, self.__class__)

    # Entities are not frozen, should not be hashed or used in sets, use the uid directly if necessary
    # def __hash__(self) -> int:
    #     return hash((self.uid, self.__class__))

    # Let's not use state-hash as an identifier so it isn't called repeatedly
    def _state_hash(self) -> bytes:
        # Data thumbprint for auditing
        state_data = self.unstructure()
        logger.debug(state_data)
        return hashing_func(state_data)

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        """
        Structure a string-keyed dict of unflattened data into an object of its
        declared class type.
        """
        _data = dict(data)  # local copy
        obj_cls = _data.pop("obj_cls", cls)
        # This key _should_ be unflattened by the serializer when necessary, but if not,
        # we can try to unflatten it as the qualified name against Entity
        if isinstance(obj_cls, str):
            obj_cls = Entity.dereference_cls_name(obj_cls)
        if obj_cls is not cls:
            # Call the correct class's structure() method without an obj_cls override
            return obj_cls.structure(_data)
        return cls(**_data)

    @classmethod
    def dereference_cls_name(cls, name: str) -> Type[Self]:
        # todo: Should memo-ize this, move into utils mixin, StructuredModel protocol?
        if name == cls.__qualname__:
            return cls
        for _cls in cls.__subclasses__():
            if x := _cls.dereference_cls_name(name):
                return x

    def unstructure(self) -> StringMap:
        """
        Unstructure an object into a string-keyed dict of unflattened data.
        """
        # Also excludes any fields attrib 'exclude' (Pydantic only, not dataclass)
        exclude = set(self._fields(serialize=False))
        # logger.debug(f"exclude={exclude}")
        data = self.model_dump(
            # exclude_unset=True,  # too many things are mutated after being initially unset
            exclude_none=True,
            exclude_defaults=True,
            exclude=exclude,
        )
        data['uid'] = self.uid  # uid is considered Unset initially
        data["obj_cls"] = self.__class__
        # The 'obj_cls' key _may_ be flattened by some serializers.  If flattened as qual name,
        # it can be unflattened with `Entity.dereference_cls_name`
        return data

EntityT = TypeVar('EntityT', bound=Entity)
MatchPredicate: TypeAlias = Callable[[Entity], bool]


# Extension mixins

class Selectable(BaseModel):
    """
    Selectable(selection_criteria: dict[str, ~typing.Any])

    Inverse-matching mixin for publishing selection criteria.

    Why
    ----
    Lets providers (domains, templates, handlers) declare what they *satisfy* so a
    tester entity can call :meth:`Entity.matches` against those criteria.

    Key Features
    ------------
    * **Static or dynamic** – override :meth:`get_selection_criteria` to compute
      criteria from labels/types/state.
    * **Helpers** – :meth:`satisfies` (entity → criteria) and
      :meth:`filter_for_selector` (bulk filter).

    API
    ---
    - :attr:`selection_criteria` – default criteria dict (may include `predicate`).
    - :meth:`get_selection_criteria` – return criteria for inverse match.
    - :meth:`satisfies` – :meth:`selector.matches(**selection_criteria)<matches>` sugar.
    - :meth:`filter_for_selector` – iterator over values satisfying a selector.
    """
    selection_criteria: StringMap = Field(default_factory=dict)
    # include a selection MatchPredicate that will run on the _tester_ with the key
    # {'predicate': lambda x: True}

    def get_selection_criteria(self) -> StringMap:
        # override this to create dynamic selections
        return copy(self.selection_criteria)

    @classmethod
    def filter_for_selector(cls, values: Iterable[Self], *, selector: Entity) -> Iterator[Self]:
        # or could use the symmetric helper `lambda x: helper x.satisfies(selector)`
        return filter(lambda x: hasattr(x, 'get_selection_criteria') and selector.matches(**x.get_selection_criteria()), values)

    def satisfies(self, selector: Entity) -> bool:
        return selector.matches(**self.get_selection_criteria())


class Conditional(BaseModel):
    """
    Conditional(predicate: ~typing.Callable[[Entity, dict], bool])

    Lightweight predicate gate for availability checks.

    Why
    ----
    Wraps a callable predicate so conditionals can be stored, serialized, and
    evaluated consistently across domains/handlers.

    Key Features
    ------------
    * **Callable** – `predicate(ns)` returns truthy/falsey.
    * **Portable** – designed for simple lambdas; richer expressions can be layered later.

    API
    ---
    - :attr:`predicate` – `(ns: dict) -> bool`.
    - :meth:`available` – evaluate predicate against a namespace.
    """
    predicate: Predicate = Field(default=lambda x: True)

    def available(self, ns: StringMap) -> bool:
        return self.predicate(ns) is True
