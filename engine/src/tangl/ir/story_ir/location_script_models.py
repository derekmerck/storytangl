from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from pydantic import Field

from tangl.type_hints import Expr, UniqueLabel, StringMap
from tangl.ir.core_ir import BaseScriptItem
from .actor_script_models import ActorScript
from .asset_script_models import AssetsScript

if TYPE_CHECKING:
    from .story_script_models import ScopeSelector


class LocationScript(BaseScriptItem):

    assets: list[AssetsScript] = None   # assets associated with the loc
    extras: list[ActorScript] = None   # extras associated with the loc

    scope: ScopeSelector | None = Field(
        None,
        description="Where this template is valid (``None`` makes it global).",
    )


class SettingScript(BaseScriptItem):
    location_template: Optional[LocationScript] = None
    location_ref: Optional[UniqueLabel] = None
    location_criteria: Optional[StringMap]
    location_conditions: Optional[list[Expr]] = None

    assets: list[AssetsScript] = None   # assets associated with the setting
    extras: list[ActorScript] = None   # extras associated with the setting


