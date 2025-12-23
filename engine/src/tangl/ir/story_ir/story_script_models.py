"""
The story script schema is defined as Pydantic models.

World includes a 'ScriptManager' class that ingests story scripts
and instantiates new stories from them.

Text and comment fields are presumed to be in markdown format.
"""

from __future__ import annotations
import logging
from typing import Any, Optional, Iterator

from pydantic import BaseModel, Field, field_validator

from tangl.type_hints import Hash, StringMap, UniqueLabel
from tangl.core import Registry
from tangl.ir.core_ir import BaseScriptItem, MasterScript
from tangl.core.graph.scope_selectable import ScopeSelectable
from .scene_script_models import SceneScript, BlockScript, MenuBlockScript
from .actor_script_models import ActorScript, RoleScript
from .location_script_models import LocationScript, SettingScript
from .asset_script_models import AssetsScript

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class StoryScript(MasterScript, BaseScriptItem):

    label: UniqueLabel = Field(..., description="A unique name for this script.") # req for indexing
    locals: Optional[StringMap] = Field(None, alias="globals", description="Global variables that will be pre-set when a story is created.")

    scenes: list[SceneScript] | dict[UniqueLabel, SceneScript] = Field(..., json_schema_extra={'child_scripts': True})        # scene1: { blocks: { block1:
    actors: list[ActorScript] | dict[UniqueLabel, ActorScript] = Field(None, json_schema_extra={'child_scripts': True})  # alice: { name: ...
    locations: list[LocationScript] | dict[UniqueLabel, LocationScript] = Field(None, json_schema_extra={'child_scripts': True})  # a_dark_place: { name: ...
    assets: list[AssetsScript] = None                                  # wearables: { shirt: { text: ...
    # assets: dict[ClassName, dict[UniqueLabel, AssetScript]] = None
    # todo: include examples in json_schema_extras

    # Template-map {templ_name: {attrib: default}}
    templates: Optional[ dict[UniqueLabel, dict[str, Any]] ] = None

    # @field_validator('scenes', 'actors', 'locations', mode="before")
    # @classmethod
    # def __set_label_from_key(cls, value: dict[UniqueLabel, StringMap]) -> dict[UniqueLabel, StringMap]:
    #     return cls._set_label_from_key(value)

    def create_template_registry(self) -> Registry[BaseScriptItem]:
        # decomposes a script into script items and registers them
        # marking scope where relevant
        reg = Registry(label=f"{self.label}_templates")
        for item in self.visit():
            reg.add(item)
        return reg


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
