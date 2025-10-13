from pydantic import ConfigDict

from tangl.type_hints import UniqueLabel
# from tangl.media import MediaNode, JournalMediaItem
from tangl.journal.content import KvFragment
from tangl.service.response import BaseResponse
from tangl.ir.core_ir import ScriptMetadata


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
