from __future__ import annotations
from typing import TYPE_CHECKING, Self

from pydantic import ConfigDict

from tangl.journal.content import KvFragment

from tangl.ir.core_ir import ScriptMetadata
from tangl.service.response.native_response import InfoModel
from tangl.type_hints import UniqueLabel

if TYPE_CHECKING:
    from tangl.story.fabula import World


class WorldInfo(InfoModel, ScriptMetadata):
    label: UniqueLabel

    @classmethod
    def from_world(cls, world: World, **kwargs: object) -> Self:
        return cls(label=world.label, **world.script_manager.get_story_metadata(), **kwargs)


class WorldList(KvFragment):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"key": "TangldWorld", "value": "my_world", "style_hints": {"color": "orange"}},
        }
    )


class WorldSceneList(KvFragment):
    ...
