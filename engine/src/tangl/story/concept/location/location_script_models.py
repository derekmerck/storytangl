from typing import Optional

from pydantic import Field

from tangl.type_hints import Expr, UniqueLabel, StringMap
from tangl.scripting import BaseScriptItem
from ..actor import ActorScript
from ..asset import AssetScript


class LocationScript(BaseScriptItem):

    assets: list[AssetScript] = None   # assets associated with the loc
    extras: list[ActorScript] = None   # extras associated with the loc


class SettingScript(BaseScriptItem):
    location_template: Optional[LocationScript] = None
    location_ref: Optional[UniqueLabel] = None
    location_criteria: Optional[StringMap]
    location_conditions: Optional[list[Expr]] = None

    assets: list[AssetScript] = None   # assets associated with the setting
    extras: list[ActorScript] = None   # extras associated with the setting


