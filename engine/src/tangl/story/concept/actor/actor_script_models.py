from typing import Optional

from tangl.type_hints import Expr, UniqueLabel, StringMap
from tangl.scripting import BaseScriptItem
from ..asset import AssetScript
from tangl.narrative.lang.gens import Gens


class ActorScript(BaseScriptItem):
    name: Optional[str] = None
    gender: Optional[Gens] = None

    # todo: consider how to reserve a look, demographics field for mechanics that may not be used?

    assets: list[AssetScript] = None     # assets associated with the actor


class RoleScript(BaseScriptItem):
    actor_template: Optional[ActorScript] = None
    actor_ref: Optional[UniqueLabel] = None
    actor_criteria: Optional[StringMap] = None
    actor_conditions: Optional[list[Expr]] = None

    assets: list[AssetScript] = None     # assets associated with the role, titles, gold badge for sherif

# class ExtrasScript ... ?
