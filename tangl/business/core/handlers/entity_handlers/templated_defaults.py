from typing import Any

from tangl.type_hints import StringMap
from tangl.business.core.entity import Entity
from tangl.business.core.handlers import TaskPipeline

on_gather_templates = TaskPipeline[Entity, dict]("on_gather_templates")
on_set_defaults = TaskPipeline[Entity, Any]("on_set_defaults")

# todo: these are unusual b/c they should be invoked on new or newly structuring
#       and should take and return a dict, not a structured object
#       similarly with on_new_entity(obj_cls) taking the obj_cls and returning
#       the proper class...

class TemplatedDefaults(Entity):

    template_maps: dict[str, StringMap] = None

    @on_gather_templates.register
    def _provide_cls_templates(self, **context) -> StringMap:
        ...
