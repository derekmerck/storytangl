from __future__ import annotations
from typing import Type, TYPE_CHECKING
import logging

from pydantic._internal._model_construction import ModelMetaclass

from tangl.type_hints import TemplateName, TemplateMap, Typelike
from .handler import SmartNewHandler

if TYPE_CHECKING:
    from tangl.entity import Entity

logger = logging.getLogger("tangl.entity.smart")

class SmartNewMetaclass(ModelMetaclass):

    def __call__(base_cls: Type[Entity],
                 *args,
                 obj_cls: Typelike = None,
                 templates: list[TemplateName] = None,
                 template_maps: list[TemplateMap] = None,
                 **kwargs):
        """
        Customized instantiation logic for Entity and its subclasses.

        It handles class casting, template application, and additional strategy hooks
        before calling the superclass __call__ method.

        Args:
            *args: Positional arguments for instantiation.
            obj_cls (Typelike, optional): The desired class type for the entity instance.
            templates (list[TemplateName], optional): List of template names to apply.
            template_maps (list[TemplateMap], optional): List of template maps to apply.
            **kwargs: Keyword arguments for instantiation.

        Returns:
            Entity: The instantiated entity object.
        """

        # Class casting logic
        # _always_ want to check this to catch singletons, not just on obj_cls
        target_class = SmartNewHandler.handle_cls(base_cls = base_cls,
                                                  obj_cls = obj_cls,
                                                  **kwargs)
        if target_class is not base_cls:
            if isinstance(target_class, base_cls):
                # It's a preexisting Singleton of some kind
                return target_class
            # Call the target class
            return target_class(*args, **kwargs)

        # We know we have the right class
        if templates:
            # Apply template logic, don't do this until we have the right class
            kwargs = SmartNewHandler.handle_kwargs(base_cls,
                                                   templates,
                                                   template_maps,
                                                   kwargs)

        # Proceed with instantiation
        instance = super().__call__(*args, **kwargs)
        return instance

