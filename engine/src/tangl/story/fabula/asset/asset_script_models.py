from pydantic import Field

from tangl.type_hints import ClassName, UniqueLabel
from tangl.scripting import BaseScriptItem

class AssetScriptItem(BaseScriptItem, extra="allow"):
    from_ref: UniqueLabel = Field(None, description="Label of reference asset to inherit traits from")

class AssetsScript(BaseScriptItem):
    obj_cls: ClassName = Field(..., alias="asset_cls")
    assets: list[AssetScriptItem] | dict[UniqueLabel, AssetScriptItem] = None

