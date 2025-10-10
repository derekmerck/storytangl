from typing import Optional

from tangl.type_hints import Expr, UniqueLabel, StringMap
from tangl.ir import BaseScriptItem
from ..asset.asset_script_models import AssetsScript
from tangl.lang.gens import Gens

MediaItemScript = BaseScriptItem


class ActorScript(BaseScriptItem):
    name: Optional[str] = None
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # at least 1 of name, full name, or first and land
    gender: Optional[Gens] = None

    # todo: consider how to reserve a look, demographics field for mechanics that may not be used?

    assets: list[AssetsScript] = None     # assets associated with the actor

    # look: Optional[LookScript] = None
    # wearables: Optional[list[AssetScript]] = Field(None, alias="outfit")
    # ornaments: Optional[OrnamentationScript] = None

    media: list[MediaItemScript] = None

class RoleScript(BaseScriptItem):
    actor_template: Optional[ActorScript] = None
    actor_ref: Optional[UniqueLabel] = None
    actor_criteria: Optional[StringMap] = None
    actor_conditions: Optional[list[Expr]] = None

    assets: list[AssetsScript] = None     # assets associated with the role, titles, gold badge for sherif

# class ExtrasScript ... ?

