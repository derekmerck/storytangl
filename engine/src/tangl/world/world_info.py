from typing import Optional, Any

from pydantic import BaseModel, field_validator, Field, ConfigDict

from tangl.type_hints import UniqueLabel
# from tangl.media import MediaNode, JournalMediaItem
from tangl.core import KvFragment

class UIConfig(BaseModel):
    model_config = ConfigDict(extras="allow")
    brand_color: str
    brand_font: str = None


class WorldInfo(BaseModel):
    label: UniqueLabel
    version: Optional[str] = None

    title: str
    author: str | list[str]
    comments: Optional[str] = Field(None, json_schema_extra={'markdown': True})

    ui_config: Optional[UIConfig] = None
    # media: Optional[list[MediaNode | JournalMediaItem]] = None

#
# class WorldListItem(KVItem):
#
#     model_config = ConfigDict(
#         json_schema_extra = {
#             'example': {'key': 'TanglWorld', 'value': 'twrld', 'style_hints': {'color': 'orange'}}
#         }
#     )

WorldList = KvFragment


# class WorldSceneItem(KVItem):
#     pass

WorldSceneList = KvFragment

