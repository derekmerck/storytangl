"""
The story script schema is defined as Pydantic models.

World includes a 'ScriptManager' class that ingests story scripts
and instantiates new stories from them.

Text and comment fields are presumed to be in markdown format.
"""

from __future__ import annotations
import logging
from typing import Any, Optional

from pydantic import Field, field_validator

from tangl.type_hints import UniqueLabel, StringMap
from tangl.ir.core_ir import BaseScriptItem, MasterScript
from .scene_script_models import SceneScript
from .actor_script_models import ActorScript
from .location_script_models import LocationScript
from .asset_script_models import AssetsScript

logger = logging.getLogger(__name__)


class StoryScript(MasterScript):

    label: UniqueLabel = Field(..., description="A unique name for this script.") # req for indexing
    locals: Optional[StringMap] = Field(None, alias="globals", description="Global variables that will be pre-set when a story is created.")

    scenes: list[SceneScript] | dict[UniqueLabel, SceneScript]         # scene1: { blocks: { block1:
    actors: list[ActorScript] | dict[UniqueLabel, ActorScript] = None  # alice: { name: ...
    locations: list[LocationScript] | dict[UniqueLabel, LocationScript] = None  # a_dark_place: { name: ...
    assets: list[AssetsScript] = None                                  # wearables: { shirt: { text: ...
    # assets: dict[ClassName, dict[UniqueLabel, AssetScript]] = None
    # todo: include examples in json_schema_extras

    # Template-map {templ_name: {attrib: default}}
    templates: Optional[ dict[UniqueLabel, dict[str, Any]] ] = None

    @field_validator('scenes', 'actors', 'locations', mode="before")
    @classmethod
    def _set_label_from_key(cls, value: dict[UniqueLabel, BaseScriptItem]):
        if isinstance(value, dict):
            for k, v in value.items():
                v.setdefault("label", k)
        return value
