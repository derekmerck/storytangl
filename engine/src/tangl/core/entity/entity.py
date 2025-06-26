from typing import Iterable, Optional, Self, Type, Protocol, Any, Callable, ClassVar, Iterator
from uuid import UUID, uuid4
import logging
import unicodedata
from functools import wraps

import shortuuid
from pydantic import Field, field_validator, ValidationInfo

from tangl.utils.base_model_plus import BaseModelPlus
from tangl.utils.sanitize_str import sanitise_str
from tangl.type_hints import UnstructuredData, Tag, Identifier

logger = logging.getLogger(__name__)
match_logger = logging.getLogger(f"{__name__}.match_logger")  # Very verbose
match_logger.setLevel(logging.INFO)


def identifier_property(func: Callable[[Any], Any]) -> property:
    func._is_identifier = True
    prop = property(func)
    return prop

class Entity(BaseModelPlus):
    uid: UUID = Field(default_factory=uuid4, json_schema_extra={'is_identifier': True})
    label_: Optional[str] = Field(None, alias="label")
    tags: set[Tag] = Field(default_factory=set)

    # MATCHING

    def matches(self, **criteria) -> bool:
        for k, v in criteria.items():
            match_logger.debug(f"Matching {k}: {v}")
            has_k = f"has_{k}" if not k.startswith("has_") else k
            if hasattr(self, has_k):
                match_logger.debug(f"Checking {v!r}.{has_k}()")
                func = getattr(self, has_k)
                if not func(v):
                    match_logger.debug(f"Failed checking {has_k}")
                    return False
            elif getattr(self, k, None) != v:
                match_logger.debug(f"Failed comparing {self!r}.{k} == {v}")
                return False
        return True

    @classmethod
    def filter_by_criteria(cls, *entities, **criteria):
        return filter(lambda e: e.matches(**criteria), *entities)

    def has_cls(self, obj_cls: Type[Self]) -> bool:
        if obj_cls is None:
            return True
        return isinstance(self, obj_cls)

    def iter_aliases(self) -> Iterator[Identifier]:

        def _iter_annotated_field_values():
            for fname, field in self.model_fields.items():
                field_extras = field.json_schema_extra or {}
                if field_extras.get("is_identifier", False):
                    prop_value = getattr(self, fname)
                    match_logger.debug(f"Found identifier attrib {fname} = {prop_value}")
                    if isinstance(prop_value, Identifier):
                        yield prop_value
                    elif isinstance(prop_value, Iterable):
                        yield from prop_value

        def _iter_annotated_class_values():
            for base in self.__class__.__mro__:
                for v in vars(base).values():
                    if isinstance(v, property) and getattr(v.fget, "_is_identifier", False):
                        match_logger.debug(f"Found identifier property {v.fget.__name__}")
                        prop_value = v.fget(self)
                        if isinstance(prop_value, Identifier):
                            yield prop_value
                        elif isinstance(prop_value, Iterable):
                            yield from prop_value

        yield from _iter_annotated_field_values()
        yield from _iter_annotated_class_values()

    def has_identifier(self, *alias: Identifier) -> bool:
        if len(alias) == 1 and alias[0] is None:
            raise ValueError("Undefined check for empty identifier alias")
        identifiers = set(self.iter_aliases())
        for a in alias:
            if a in identifiers:
                return True
        return False

    # ironic alias for has_alias
    has_alias = has_identifier

    def _attrib_is_superset_of(self, attrib: str, *items) -> bool:
        data = getattr(self, attrib, None)
        if not isinstance(data, set):
            raise ValueError(f"Invalid attrib for contains, {attrib!r} is not a set")
        if len(items) == 1 and items[0] is None:
            # If we are trying to match "None", we want to know if this attrib is empty
            return len(data) == 0  # check for empty
        if len(items) == 1 and isinstance(items[0], (list, set)):
            # Only one item was provided
            items = items[0]
        return set(items).issubset(data)

    def has_tags(self, *tags: Tag) -> bool:
        match_logger.debug(f"Comparing query tags {tags} against {self!r} with tags={self.tags}")
        return self._attrib_is_superset_of("tags", *tags)

    # STRUCTURING

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls", cls)
        return obj_cls(**data)

    @wraps(BaseModelPlus.model_dump)
    def model_dump(self, **kwargs) -> UnstructuredData:
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("exclude_defaults", True)
        kwargs.setdefault("by_alias", True)
        data = super().model_dump(**kwargs)
        data['uid'] = self.uid  # May not be included b/c it's considered default/unset
        data['obj_cls'] = self.__class__
        return data

    def unstructure(self, **kwargs) -> UnstructuredData:
        return self.model_dump(**kwargs)

    # UTILITIES

    @field_validator('label_', mode="after")
    @classmethod
    def _sanitize_label(cls, value):
        if isinstance(value, str):
            value = sanitise_str(value)
        return value

    @identifier_property
    def label(self) -> str:
        return self.label_ or self.short_uid

    @label.setter
    def label(self, value: str):
        self.label_ = value

    @identifier_property
    def short_uid(self) -> str:
        return shortuuid.encode(self.uid)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{self.label}>"

    dirty: bool = False
    # indicator that entity has been tampered with, invalidates certain debugging
