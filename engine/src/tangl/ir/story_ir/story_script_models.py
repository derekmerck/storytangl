"""
The story script schema is defined as Pydantic models.

World includes a 'ScriptManager' class that ingests story scripts
and instantiates new stories from them.

Text and comment fields are presumed to be in markdown format.
"""

from __future__ import annotations
import logging
from typing import Any, Optional, Iterator, Type

from pydantic import BaseModel, Field, field_validator

from tangl.type_hints import Hash, StringMap, UniqueLabel
from tangl.core import Registry, Entity
from tangl.ir.core_ir import BaseScriptItem, MasterScript
from .scene_script_models import SceneScript, BlockScript, MenuBlockScript
from .actor_script_models import ActorScript, RoleScript
from .location_script_models import LocationScript, SettingScript
from .asset_script_models import AssetsScript

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class StoryScript(MasterScript):

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        from tangl.story.story_graph import StoryGraph
        return StoryGraph

    label: UniqueLabel = Field(..., description="A unique name for this script.") # req for indexing
    locals: Optional[StringMap] = Field(None, alias="globals", description="Global variables that will be pre-set when a story is created.")

    scenes: list[SceneScript] | dict[UniqueLabel, SceneScript] = Field(..., json_schema_extra={'visit_field': True})        # scene1: { blocks: { block1:
    actors: list[ActorScript] | dict[UniqueLabel, ActorScript] = Field(None, json_schema_extra={'visit_field': True})  # alice: { name: ...
    locations: list[LocationScript] | dict[UniqueLabel, LocationScript] = Field(None, json_schema_extra={'visit_field': True})  # a_dark_place: { name: ...
    assets: list[AssetsScript] = None                                  # wearables: { shirt: { text: ...
    # assets: dict[ClassName, dict[UniqueLabel, AssetScript]] = None
    # todo: include examples in json_schema_extras

    # Template-map {templ_name: {attrib: default}}
    templates: Optional[ dict[UniqueLabel, dict[str, Any]] ] = None

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> StoryScript:
        return cls.model_validate(data)



_types_namespace = {
    "Hash": Hash,
    "ActorScript": ActorScript,
    "LocationScript": LocationScript,
    "RoleScript": RoleScript,
    "SettingScript": SettingScript,
    "BlockScript": BlockScript,
    "MenuBlockScript": MenuBlockScript,
    "SceneScript": SceneScript,
    "StoryScript": StoryScript,
    "MasterScript": MasterScript,
}

BaseScriptItem.model_rebuild(_types_namespace=_types_namespace)
ActorScript.model_rebuild(_types_namespace=_types_namespace)
LocationScript.model_rebuild(_types_namespace=_types_namespace)
RoleScript.model_rebuild(_types_namespace=_types_namespace)
SettingScript.model_rebuild(_types_namespace=_types_namespace)
BlockScript.model_rebuild(_types_namespace=_types_namespace)
MenuBlockScript.model_rebuild(_types_namespace=_types_namespace)
SceneScript.model_rebuild(_types_namespace=_types_namespace)
StoryScript.model_rebuild(_types_namespace=_types_namespace)
MasterScript.model_rebuild(_types_namespace=_types_namespace)
