from __future__ import annotations
from typing import TYPE_CHECKING, Self

from pydantic import ConfigDict

from tangl.type_hints import UniqueLabel
# from tangl.media import MediaNode, JournalMediaItem
from tangl.journal.content import KvFragment
from tangl.service.response import BaseResponse
from tangl.ir.core_ir import ScriptMetadata

if TYPE_CHECKING:
    from tangl.story.fabula import World


class WorldInfo(BaseResponse, ScriptMetadata):
    # revision, license, etc. should probably just inherit this data from
    # the script manager metadata...
    label: UniqueLabel

    @classmethod
    def from_world(cls, world: World, **kwargs) -> Self:
        return cls(
            label=world.label,
            **world.script_manager.get_story_metadata(),
        )

class WorldList(KvFragment):

    model_config = ConfigDict(
        json_schema_extra = {
            'example': {'key': 'TangldWorld', 'value': 'my_world', 'style_hints': {'color': 'orange'}}
        }
    )


class WorldSceneList(KvFragment):
    ...
