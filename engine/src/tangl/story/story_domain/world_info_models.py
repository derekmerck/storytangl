from typing import Optional, Any

from pydantic import BaseModel, field_validator, Field, ConfigDict

from tangl.type_hints import UniqueLabel
# from tangl.media import MediaNode, JournalMediaItem
from tangl.utils.response_models import BaseResponse, KvItem
from tangl.scripting.script_metadata_model import ScriptMetadata


class WorldInfo(ScriptMetadata):
    label: UniqueLabel


class WorldListItem(KvItem):

    model_config = ConfigDict(
        json_schema_extra = {
            'example': {'key': 'TangldWorld', 'value': 'my_world', 'style_hints': {'color': 'orange'}}
        }
    )

WorldList = list[WorldListItem]


class WorldSceneItem(KvItem):
    pass

WorldSceneList = list[WorldSceneItem]

