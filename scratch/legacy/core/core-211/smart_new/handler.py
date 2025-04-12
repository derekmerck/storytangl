from __future__ import annotations
import copy
from typing import Type, TYPE_CHECKING, Mapping, Any
import logging
from collections import ChainMap

from tangl.type_hints import TemplateName, TemplateMap, Typelike
from ..base_handler import BaseEntityHandler

if TYPE_CHECKING:
    from tangl.entity import Entity

logger = logging.getLogger("tangl.entity.smart")

class SmartNewHandler(BaseEntityHandler):
    """
    SmartNewHandler provides hooks for entities to modify their base class or instantiation
    parameters before object creation.

    It defines two strategies that can be implemented in entities using this metaclass:
    - normalize_class_strategy: Allows modifying the base class before instantiation.
    - gather_template_maps_strategy: Allows adding additional template maps for default parameter values.
    """

    # --------------------
    # Class assignment methods
    # --------------------

    @classmethod
    def normalize_class_strategy(cls, func):
        return cls.strategy(func, 'normalize_class_strategy')

    @classmethod
    def handle_cls(cls, base_cls: Type[Entity], obj_cls: Typelike = None, **kwargs) -> Entity | Type[Entity]:
        """
        Invoke the 'normalize_class_strategy' hooks to potentially modify the base class
        before instantiation.

        Args:
            base_cls (Type[Entity]): The base class for the entity.
            obj_cls (Typelike, optional): The desired class type for the entity instance.
            **kwargs: Additional keyword arguments passed to the strategy hooks.

        Returns:
            Entity | Type[Entity]: The potentially modified class for instantiation.
        """
        new_cls = cls.invoke_strategies(None,
                                        entity_cls=base_cls,
                                        obj_cls=obj_cls,
                                        strategy_annotation="normalize_class_strategy",
                                        result_handler="first",
                                        **kwargs)
        if new_cls:
            return new_cls
        return base_cls

    # --------------------
    # Templating methods
    # --------------------

    @classmethod
    def gather_template_maps_strategy(cls, func):
        return cls.strategy(func, 'gather_template_maps_strategy')

    @classmethod
    def handle_kwargs_strategy(cls, func):
        return cls.strategy(func, 'handle_kwargs_strategy')

    @classmethod
    def handle_kwargs(cls,
                      base_cls: Type[Entity],
                      templates: list[TemplateName] = None,
                      template_maps: list[TemplateMap] = None,
                      kwargs: dict[str, Any] = None) -> dict:
        """
        Merge default parameter values from templates and additional template maps provided by
        the 'gather_template_maps_strategy' hooks.

        Args:
            base_cls (Type[Entity]): The base class for the entity.
            templates (list[TemplateName]): List of template names to apply.
            template_maps (list[TemplateMap]): List of template maps to apply.
            kwargs (dict[str, Any]): The initial keyword arguments for instantiation.

        Returns:
            dict: The merged keyword arguments with default values from templates and additional maps.
        """
        kwargs = kwargs or {}

        templates = templates or kwargs.pop('templates', [])
        template_maps = template_maps or kwargs.pop('template_maps', [])
        extra_template_maps = cls.invoke_strategies(None,
                                                    entity_cls=base_cls,
                                                    strategy_annotation="gather_template_maps_strategy",
                                                    result_handler="flatten")
        if extra_template_maps:
            template_maps += extra_template_maps

        default_kwargs = cls.aggregate_templates(templates, template_maps)

        for k, v in default_kwargs.items():
            kwargs.setdefault(k, v)

        updated_kwargs = cls.invoke_strategies(None,
                                               entity_cls=base_cls,
                                               strategy_annotation="handle_kwargs_strategy",
                                               result_handler="merge",
                                               **kwargs)
        if updated_kwargs:
            kwargs = updated_kwargs

        return kwargs

    @classmethod
    def aggregate_templates(cls, templates: list[TemplateName], template_maps: list[TemplateMap]) -> Mapping:

        default_kwargs = ChainMap()
        handled_templates = set()

        def handle_one_template(template_name: TemplateName) -> Mapping | None:
            if template_name in handled_templates:
                return
            else:
                handled_templates.add(template_name)

            for template_map in template_maps:
                if template_name in template_map:
                    this_template = copy.deepcopy( template_map[template_name] )
                    new_templates = this_template.pop('templates', None)
                    if new_templates:
                        # extend the queue
                        new_templates = [ n for n in new_templates if n not in handled_templates ]
                        templates.extend(new_templates)
                    return this_template

        while templates:
            template_name = templates.pop(0)  # it's a queue
            res = handle_one_template(template_name)
            if res:
                default_kwargs.maps.append(res)

        return default_kwargs
