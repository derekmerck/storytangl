from __future__ import annotations
from collections import ChainMap
from typing import Any, ClassVar, Type, Mapping
import logging
import copy

from pydantic import BaseModel, model_validator, Field

from tangl.type_hints import UniqueLabel
from tangl.utils.reduce_default import reduce_default
from tangl.core.handler import BaseHandler, Priority
from tangl.core.entity import Entity


logger = logging.getLogger(__name__)

# Type names, to keep them clear
TemplateName = UniqueLabel            # the name for a group of default attribute values
TemplateDefaults = Mapping[str, Any]  # a named group of (attrib name, default values) pairs
TemplateMap = dict[TemplateName, TemplateDefaults]   # an indexed collection of named groups of default values

DISALLOWED_KEYS = {'uid': 'Setting `uid` with a template violates its uniqueness guarantee.',
                   'obj_cls': 'Setting `obj_cls` within a template leads to ambiguous initialization patterns and potential recursions.'}

# todo: I think this _could_ get redone to remove it from the 'new' process and put it in as a pydantic pre-init (ie, override __init__ and call for template processing before handing args over to regular init), would "on_new" still want to allow kwarg manipulation anyway?

class TemplateHandler(BaseHandler):
    """
    Handles the aggregation and processing of default attribute value templates for
    Entity instance creation.

    A list of template names is prioritized left -> right and processed/merged
    from right -> left, so more important overrides less important

    A list of template maps represents different template maps from different sources
    that need to be merged, template _maps_ are also prioritized left -> right and
    processed/merged in reverse order.

    Pre-process entry point is `process_templates(cls, names, data)`

    Then there are 3 phases in pre-processing:
      - `gather_template_maps`: Collect all template maps from all registered sources for this class/domain (extensible)
      - `aggregate_defaults(names, maps)`:  Create a master attribute-value default map for a set of template names and maps
      - `merge_defaults(maps, data)`: Merge defaults from attribute-value templates into data as a preprocess for initialization.

    Post-process entry point is `reduce_defaults(instance)`
      - `reduce_defaults(inst)`: Process any data fields that require random sampling from a distribution to convert the template distribution to a discrete value

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
    >>> TemplatedDefaultsHandler.aggregate_defaults(['labrador'], [template_map])
    {'has_tail': True, 'sheds': False}
    """

    # @BaseHandler.task_signature
    # @staticmethod
    # def on_gather_templates(entity: HasTemplates, **kwargs) -> TemplateMap:
    #     ...

    @classmethod
    def strategy(cls, task_id: UniqueLabel = "on_gather_templates",
                 domain: UniqueLabel = "global",
                 priority: int = Priority.NORMAL ):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def check_for_disallowed_keys(cls, data: Mapping[str, Any]):
        for k, err in DISALLOWED_KEYS.items():
            if k in data:
                raise ValueError(f"Key {k} not allowed in template {err}")

    @BaseHandler.strategy('on_new', priority=Priority.LATE)
    @staticmethod
    def _process_templates(base_cls: Type[Entity], *,
                           template_names: list[TemplateName] = None,
                           template_maps: list[TemplateMap] = None,
                           **kwargs) -> tuple[Type, dict]:

        if not issubclass(base_cls, HasTemplates):
            logger.debug(f"Not a templated class, nothing to do.")
            return base_cls, kwargs

        if not template_names:
            logger.debug(f"No template names, nothing to do.")
            return base_cls, kwargs

        logger.debug(f"found template names: {template_names}")

        # gather templates
        template_maps = template_maps or []
        template_maps_ = TemplateHandler.execute_task(base_cls, "on_gather_templates", result_mode="flatten", **kwargs)  # type: list[TemplateMap]
        # We _don't_ want this to be a regular chain-map because different maps may have
        # different sections of a particular template's defaults.
        if template_maps_:
            template_maps.extend(template_maps_)  # merge whatever was passed in
        if not template_maps:
            raise RuntimeError("Found templates but no template maps?")

        logger.debug(f"gathered template map sources:  {template_maps}")

        kwargs = TemplateHandler.process_templates(data=kwargs,
                                                   template_names=template_names,
                                                   template_maps=template_maps)
        return base_cls, kwargs

    @classmethod
    def process_templates(cls,
                          data: dict,
                          template_names: list[TemplateName] = None,
                          template_maps: list[TemplateMap] = None):
        """
        Modifies kwargs based on template parameters and template maps for defaults.
        Resolves late so the base_cls is known and can be used as a source for template
        maps.

        Template maps may be included in many different places, by the invoking factory,
        the instance class, the graph, passed as kwargs, etc.

        This function gathers and aggregates the relevant maps, then sets defaults in the
        pre-init-data as possible.
        """
        # normalize input values
        data = copy.deepcopy(data)
        template_names = template_names or data.pop('template_names', [])  # type: list[TemplateKey]
        if not template_names:
            logger.debug(f"No template names, nothing to do.")
            return data
        template_maps = template_maps or data.pop('template_maps', [])  # type: list[TemplateMap]

        # aggregate
        template_defaults = TemplateHandler.aggregate_templates(template_names, template_maps)

        if not template_defaults:
            raise ValueError(f"Template keys provided, but no defaults found, nothing to do.")

        # raises KeyError if disallowed keys have been introduced
        TemplateHandler.check_for_disallowed_keys(template_defaults)

        logger.debug(f"found defaults:  {str(template_defaults)}")

        # update data with defaults
        data = copy.deepcopy(data)
        for k, v in template_defaults.items():
            data.setdefault(k, v)
        logger.debug(f"updated data:  {str(data)}")

        return data

    @classmethod
    def aggregate_templates(cls, template_keys: list[TemplateName], template_maps: list[TemplateMap]) -> TemplateDefaults:
        """
        Recursively merges template maps for given templates to create a unified
        dict of default values.

        This method also checks for the presence of disallowed keys (uid, obj_cls) in
        the defaults.

        Args:
            template_names (list[TemplateName): The key identifying the template to retrieve.
            template_maps (list[TemplateMap): The registry containing the template definitions.

        Returns:
            TemplateDefaults: The final string-map { field_name: default_value } template

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
                    new_template_keys = template_defaults.pop('template_names', [])

                    # Process new templates first (recursively)
                    for new_key in new_template_keys:
                        process_template_key(new_key)

                    accumulator.maps.insert(0, template_defaults)

        for template_key in reversed(template_keys):
            process_template_key(template_key)

        return dict(accumulator)

    @classmethod
    def reduce_defaults(cls, node: HasTemplates) -> HasTemplates:
        """
        Post-process an instance to reduce fields with sampled distributions
        to discrete values.  Called as a validator and executed in-place.
        """
        for field, field_info in node.model_fields.items():
            field_schema_extras = field_info.json_schema_extra or {}
            if field_schema_extras.get('reduce', False):
                value = getattr(node, field)
                value_ = reduce_default(value)
                if value != value_:
                    setattr(node, field, value_)
        return node

class HasTemplates(BaseModel):
    """
    Provides a mechanism for entities to utilize templates for dynamic content generation.

    Key Features:
      - `class_default_template_map`: A class-level mapping of attribute templates for new instances.
    """
    class_template_map: ClassVar[TemplateMap] = dict()

    @TemplateHandler.strategy()
    def _get_class_template_map(cls, **kwargs) -> list[TemplateMap]:
        return [ cls.class_template_map ]

    @model_validator(mode='after')
    def _reduce_defaults(self):
        """This reduces independently, after instance init, any dependent sampling should
        be done as a pre-process to instantiation."""
        node = TemplateHandler.reduce_defaults(self)
        return node

    template_names: list[TemplateName] = Field(None, init_var=True)
