from __future__ import annotations
from collections import ChainMap
from typing import Any, ClassVar, Type, Callable, Mapping
import logging
import copy

from pydantic import BaseModel, model_validator

from tangl.utils.reduce_default import reduce_default
from ..base_handler import BaseEntityHandler
from ..entity import Entity, EntityType
from ..singleton import UniqueLabel

logger = logging.getLogger("tangl.templates")

TemplateName = UniqueLabel            # the name for a group of default attribute values
TemplateDefaults = Mapping[str, Any]  # a named group of (attrib name, default values) pairs
TemplateMap = dict[TemplateName, TemplateDefaults]   # an indexed collection of named groups of default values

DISALLOWED_KEYS = {'uid': 'Setting `uid` with a template violates its uniqueness guarantee.',
                   'obj_cls': 'Setting `obj_cls` with a template leads to ambiguous initialization patterns.'}

# todo: consider some specific, clear way to handle changing 'node_cls' in templates.  For now,
#       that is only disallowed because of ambiguity in how to handle it.

class TemplateHandler(BaseEntityHandler):
    """
    Handles the aggregation and processing of default attribute value templates for Entity instance
    creation.

    A list of template names is prioritized left -> right and processed/merged
    from right -> left, so more important overrides less important

    A list of template maps represents different template maps from different sources
    that need to be merged, template _maps_ are also prioritized left -> right and
    processed/merged in reverse order.

    Key Features:
      - `process_templates(names, maps, data)`: Merge defaults from attribute-value templates into data as a preprocess for initialization.
      - `aggregate_templates(names, maps)`:  Create a master attribute-value default map for a set of template names and maps
      - `reduce_defaults(data)`: Process any data fields that require random sampling from a distribution to convert the template distribution to a discrete value

    Raises:
        ValueError: If disallowed keys like 'uid' or 'obj_cls' are used in templates.

    >>> template_map = {
    ...   'animal': {
    ...      'has_tail': 'Maybe'},
    ...   'dog': {
    ...      'templates': ['animal'],
    ...      'has_tail': True,
    ...      'sheds': True },
    ...    'labrador': {
    ...      'templates': ['dog'],
    ...      'sheds': False } }
    >>> TemplateHandler.aggregate_defaults(['labrador'], [template_map])
    {'has_tail': True, 'sheds': False}
    """

    default_strategy_annotation = "gather_template_maps_strategy"

    @classmethod
    def gather_template_maps_strategy(cls, func: Callable):
        return cls.strategy(func)

    @classmethod
    def check_for_disallowed_keys(cls, data: Mapping[str, Any]):
        for k, err in DISALLOWED_KEYS.items():
            if k in data:
                raise ValueError(f"Key {k} not allowed in template {err}")

    @classmethod
    def process_templates(cls,
                          data: dict[str, Any],
                          entity_cls: Type[Templated] = None,
                          templates: list[TemplateName] = None,
                          template_maps: list[TemplateMap] = None) -> dict[str, Any]:
        """
        This is the entry point for any node that is preprocessing templates.

        Template maps may be included in many different places, by the invoking factory,
        the instance class, the graph, passed as kwargs, etc.

        This function gathers and aggregates the relevant maps, makes selections for all
        random-ish values, and sets defaults in the pre-init-data as possible.
        """
        # normalize input values
        data = copy.deepcopy(data)
        templates = templates or data.pop('templates', [])            # type: list[TemplateKey]
        if not templates:
            return data
        template_maps = template_maps or data.pop('template_maps', []) # type: list[TemplateMap]

        # gather
        if entity_cls:
            template_maps += cls.invoke_strategies(None, entity_cls=entity_cls, result_handler='flatten')
        if not template_maps:
            raise RuntimeError("Found templates but no template maps?")

        logger.debug(f"template names: {templates}")
        logger.debug(f"template maps:  {template_maps}")

        # aggregate
        defaults = cls.aggregate_templates(templates, template_maps)
        logger.debug( f"found defaults: {defaults}" )

        # update data with defaults
        for k, v in defaults.items():
            data.setdefault(k, v)

        logger.debug( f"updated data: {data}" )

        # finally, confirm that no invalid keys have been introduced
        cls.check_for_disallowed_keys(data)

        logger.debug( f"new data: {data}" )

        return data

    @classmethod
    def aggregate_templates(cls, template_keys: list[TemplateName], template_maps: list[TemplateMap]):
        """
        Recursively merges template maps for given templates to create a unified
        dict of default values.

        This method also checks for the presence of disallowed keys (uid, obj_cls) in
        the defaults.

        Args:
            templates (list[TemplateName): The key identifying the template to retrieve.
            template_maps (list[TemplateMap): The registry containing the template definitions.

        Returns:
            tuple[Template, list[TemplateName]]: The template and a list of associated template keys.

        Raises:
            ValueError: If disallowed keys are present in the template.
        """
        accumulator = ChainMap()  # Use a chainmap as an accumulator

        # keys may be added recursively by templates
        processed_keys = set()

        def process_template_key(template_key):
            nonlocal processed_keys, accumulator, template_maps, process_template_key
            if template_key in processed_keys:
                return
            processed_keys.add(template_key)

            for template_map in reversed(template_maps):
                if template_key in template_map:
                    template_defaults = copy.deepcopy(template_map[template_key])
                    new_template_keys = template_defaults.pop('templates', [])

                    # Process new templates first (recursively)
                    for new_key in new_template_keys:
                        process_template_key(new_key)

                    accumulator.maps.insert(0, template_defaults)

        for template_key in reversed(template_keys):
            process_template_key(template_key)

        return dict(accumulator)

    @classmethod
    def reduce_defaults(cls, node: Templated):
        default_reduce_flag = getattr(node, "default_reduce_flag", False)
        for field, field_info in node.model_fields.items():
            schema_extras = field_info.json_schema_extra or {}
            if schema_extras.get('reduce', default_reduce_flag):
                value = getattr(node, field)
                value_ = reduce_default(value)
                if value != value_:
                    setattr(node, field, value_)

class Templated(BaseModel):
    """
    Provides a mechanism for entities to utilize templates for dynamic content generation.

    Key Features:
      - `class_template_map`: A class-level mapping of attribute templates for new instances.
      - `_process_templates()`: A class method that preprocesses templates before instantiation, leveraging `TemplateHandler`.
      - `_reduce_defaults()`: A class method that post-processes the instance to reduce fields with sampled distributions to discrete values
    """
    class_template_map: ClassVar[TemplateMap] = dict()
    default_reduce_flag: ClassVar[bool] = False
    # set per-field "reduce" extra to the opposite of this setting

    @TemplateHandler.gather_template_maps_strategy
    def _get_default_template_maps(cls) -> list[TemplateMap]:
        return [ cls.class_template_map ]

    @model_validator(mode='before')
    @classmethod
    def _process_templates(cls: EntityType, data):
        # assert 'obj_cls' not in data
        if 'templates' in data:
            data = TemplateHandler.process_templates(data, entity_cls=cls)
        # data = TemplateHandler.reduce_defaults(data, entity_cls=cls)
        # assert 'templates' not in data
        # if "obj_cls" in data:
        #     logger.debug(f"Has obj cls: {data['obj_cls']}")
        return data

    @model_validator(mode='after')
    def _reduce_defaults(self):
        # This only reduces independently, dependent sampling should get done
        # as a pre-process to instantiation
        TemplateHandler.reduce_defaults(self)
        return self
