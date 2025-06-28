from pydantic import ConfigDict

from tangl.type_hints import UniqueLabel
# from tangl.media import MediaNode, JournalMediaItem
from tangl.core.entity.fragment import KvFragment
from tangl.service.response import BaseResponse
# from tangl.scripting.script_metadata_model import ScriptMetadata

ScriptMetadata = dict

class WorldInfo(BaseResponse, ScriptMetadata):
    label: UniqueLabel


class WorldList(KvFragment):

    model_config = ConfigDict(
        json_schema_extra = {
            'example': {'key': 'TangldWorld', 'value': 'my_world', 'style_hints': {'color': 'orange'}}
        }
    )


class WorldSceneList(KvFragment):
    ...
