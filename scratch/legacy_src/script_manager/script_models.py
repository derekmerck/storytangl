"""
The story script schema is defined as Pydantic models.

World includes a 'ScriptManager' class that ingests story scripts
and instantiates new stories from them.

Text and comment fields are presumed to be in markdown format
"""

from __future__ import annotations
import logging
from typing import Any, Optional
import functools

from pydantic import BaseModel, Field, model_validator, field_validator

from tangl.type_hints import UniqueLabel, Tags, Locals, ClassName
from tangl.entity import BaseScriptItem
from tangl.media import MediaItemScript
from tangl.story.scene import SceneScript, BlockScript, ActionScript
from tangl.story.actor import ActorScript, RoleScript
from tangl.story.place import PlaceScript, LocationScript
from tangl.story.asset import AssetScript

logger = logging.getLogger("tangl.script.model")

class UiConfigModel(BaseModel):
    brand_color: str = None  # html color value

class StoryMetadata(BaseModel):
    title: str               # req
    author: str | list[str]  # req
    date: Optional[str] = None
    version: Optional[str] = None
    illustrator: Optional[str] = None
    license: Optional[str] = None
    summary: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    comments: Optional[str] = Field(default=None, alias="text")

    media: Optional[list[MediaItemScript]] = None
    ui_config: Optional[UiConfigModel] = None

    @model_validator(mode='before')
    @classmethod
    def alias_text_to_comments(cls, values):
        _value = values.get('comments') or values.get('text')
        if _value is not None:
            values['comments'] = _value
        return values

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_defaults', True)
        kwargs.setdefault('exclude_none', True)
        res = super().model_dump(**kwargs)
        return res

class StoryScript(BaseModel):
    label: UniqueLabel         # req for indexing
    metadata: StoryMetadata    # req for author, title
    tags: Optional[Tags] = None
    globals: Optional[Locals] = None

    scenes: dict[UniqueLabel, SceneScript]                         # scene1: { blocks: { block1:
    actors: dict[UniqueLabel, ActorScript] = None                  # alice: { name: ...
    places: dict[UniqueLabel, PlaceScript] = None                  # a_dark_place: { name: ...
    assets: dict[UniqueLabel, AssetScript] = None                  # wearables: { shirt: { text: ...

    # Template-map
    templates: Optional[ dict[UniqueLabel, dict[str, Any]] ] = None

    @field_validator('scenes', 'actors', 'places')
    @classmethod
    def _set_label_from_key(cls, value: dict[UniqueLabel, BaseScriptItem]):
        for k, v in value.items():
            if not v.label:
                v.label = k
        return value

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_defaults', True)
        kwargs.setdefault('exclude_none', True)
        res = super().model_dump(**kwargs)
        return res

    @classmethod
    def model_json_schema(cls, **kwargs) -> dict[str, Any]:
        schema = super().model_json_schema(**kwargs)

        # from pprint import pprint
        # pprint( schema )

        defs = schema['$defs']

        # Add the IntelliJ injection info to the 'text' and 'comments' fields

        if 'BlockScript' in defs:
            defs['BlockScript']['properties']['text']['x-intellij-language-injection'] = "Markdown"

        if 'text' in defs['StoryMetadata']['properties']:
            defs['StoryMetadata']['properties']['text']['x-intellij-language-injection'] = "Markdown"

        if 'comments' in defs['StoryMetadata']['properties']:
            defs['StoryMetadata']['properties']['comments']['x-intellij-language-injection'] = "Markdown"
        else:
            # Handle the alias from text (public alias) -> comments (field name)
            defs['StoryMetadata']['properties']['comments'] = \
                {'title': 'Comments',
                 'type': 'string',
                 'x-intellij-language-injection': 'Markdown'}

        # todo: move this into passages format and override function
        if 'PassageScript'in defs:
            defs['PassageScript']['properties']['text']['x-intellij-language-injection'] = "Markdown"

        return schema
