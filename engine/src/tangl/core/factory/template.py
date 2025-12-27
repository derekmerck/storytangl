# tangl/core/factory/template.py
from __future__ import annotations
from typing import TypeVar, Generic, Self, Type
from uuid import UUID, uuid4
from inspect import isclass
import logging

from pydantic import Field, field_validator

from tangl.type_hints import Typelike, UnstructuredData, StringMap
from tangl.core.entity import Entity, Selectable
from tangl.core.record import Record, ContentAddressable

logger = logging.getLogger(__name__)


ET = TypeVar('ET', bound=Entity)

class Template(Selectable, ContentAddressable, Record, Generic[ET]):
    """
     Semi-structured template for creating entities on demand.

     Key features:
     - Holds obj_cls as a field (unlike Entity which uses it only for structure())
     - Excludes instance metadata (uid, seq, is_dirty) from serialization
     - Provides separate paths for script serialization vs entity materialization

     Examples:
         >>> from tangl.core.graph import Node
         >>> template = Template[Node](label="guard", obj_cls=Node)
         >>>
         >>> # Serialize back to script
         >>> script_data = template.unstructure_as_template()
         >>>
         >>> # Materialize entity
         >>> entity_data = template.unstructure_for_materialize()
         >>> node = Node.structure(entity_data)
     """

    # Mark record metadata as excluded for serialization and comparison
    uid: UUID = Field(default_factory=uuid4, exclude=True, json_schema_extra={'serialize': False})
    is_dirty_: bool = Field(default=False, exclude=True, json_schema_extra={'serialize': False})
    seq: int = Field(init=False, exclude=True, json_schema_extra={'serialize': False})  # injected by Record/HasSeq
    content_hash: bytes = Field(default=None, json_schema_extra={'is_identifier': True, 'serialize': False}, exclude=True)
    # todo: we _may_ want to include this in serialize->template, but it doesn't seem to respect serialize: False??

    # obj_cls is a field (not just init param like Entity)
    obj_cls_: Typelike = Field(None, alias="obj_cls", exclude_if=lambda v: v is None)

    @field_validator("obj_cls_", mode="after")
    @classmethod
    def _hydrate_obj_cls(cls, data):
        """Hydrate string obj_cls to Python type."""
        logger.debug(f"hydrating obj_cls_ field for {cls}")
        if data is None:
            return None

        logger.debug(f"found {type(data)}{data}")

        # Hydrate string to type
        if isinstance(data, str):
            resolved = Entity.dereference_cls_name(data)
            if resolved:
                data = resolved
            else:
                raise ValueError(f"Could not resolve obj_cls {data}")

        logger.debug(f"resolved to {data}")

        # Validate that it is a class and Entity subclass (or None)
        if not (data is Entity or (isclass(data) and issubclass(data, Entity))):
            raise ValueError(f"obj_cls must be Entity or subclass, got {data}")

        return data

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        """
        Can include the default directly by overriding this function with
        a local import, so you don't have to import the template ET at
        the top level.  E.g., `get_default_obj_cls(): from story import Actor; return Actor`
        """
        return cls.get_generic_type_for(Template, default=Entity)

    @property
    def obj_cls(self) -> Type[Entity]:
        """Get obj_cls_ with fallback to default."""
        return self.obj_cls_ or self.get_default_obj_cls()

    def is_instance(self, obj_cls: type | tuple[type]) -> bool:
        """
        Check against the _latent_ type, not the Template class
        `Template[MyActor].is_instance(Actor)` -> True
        This enables Template[MyActor].match(is_instance=Actor)
        """
        if isinstance(obj_cls, tuple):
            if all(isclass(c) for c in obj_cls) and issubclass(self.obj_cls, obj_cls):
                return True
        elif isclass(obj_cls) and issubclass(self.obj_cls, obj_cls):
            return True

        # Fall back to Node hierarchy
        return super().is_instance(obj_cls)

    # Inherits label, tags as is

    # todo: could provide helper function that creates Templates automatically from an Entity class

    @classmethod
    def structure(cls, data: StringMap) -> Self:
        """
        Structure data as template.

        For clarity, prefer explicit structure_as_template() or materialize().
        """
        # todo: should just raise or issue warning?
        return cls.structure_as_template(data)

    @classmethod
    def structure_as_template(cls, data: StringMap) -> Self:
        """
        Load template from script data.

        Args:
            data: Unstructured script data with obj_cls

        Returns:
            Template instance
        """
        # Don't pop obj_cls - it's a field
        # Pydantic will validate and hydrate it
        return cls.model_validate(data)

    def materialize(self, **kwargs) -> ET:
        """
        Create entity from template.

        Args:
            **kwargs: Override template fields (use sparingly - overrides beat template data)

        Returns:
            Entity instance of type ET

        Examples:
            >>> template = Template[Node](label="guard", tags={"npc"})
            >>> node = template.materialize(obj_cls=SpecialNode, label="special_guard")  # Override class and label

        Warning:
            kwargs override template data. Use for runtime customization only.
        """
        data = self.unstructure_for_materialize()
        data.update(kwargs)

        # We don't want to call structure on the payload object cls
        # directly -- it may have been changed during the unstructure
        # for materialize call or via the kwargs.  So just let
        # Entity.structure() do its thing.
        return Entity.structure(data)

    def unstructure(self) -> UnstructuredData:
        """
        Unstructure for serialization.

        For clarity, prefer explicit unstructure_as_template() or
        unstructure_for_materialize().
        """
        # todo: should just raise or issue warning?
        return self.unstructure_as_template()

    # unstructure is the same in these cases?
    def unstructure_as_template(self) -> UnstructuredData:
        """
        Serialize template back to script format.

        Returns:
          Script data suitable for round-trip serialization
        """
        data = super().model_dump(by_alias=True,
                                  exclude_unset=True,
                                  exclude_defaults=True,
                                  exclude_none=True)
        # Ensure unset obj_cls is discarded for round-trip; if it's
        # None, super().model_dump will include the wrong templ.__class__
        logger.debug(self.model_fields_set)
        if "obj_cls_" not in self.model_fields_set:
            data.pop("obj_cls", None)
        return data

    def unstructure_for_materialize(self) -> UnstructuredData:
        # call model dump for unstructured data suitable to pass to Entity.structure
        data = super().model_dump(by_alias=True,
                                  exclude_unset=False,
                                  # dict-children may be path-less templates
                                  exclude_defaults=True,
                                  exclude_none=True)
        # Ensure obj_cls is present and correct; if it's None, super().model_dump
        # will include the wrong templ.__class__
        data["obj_cls"] = self.obj_cls
        return data
