from pydantic import Field

from tangl.type_hints import ClassName, UniqueLabel
from tangl.ir.core_ir import BaseScriptItem

class AssetScriptItem(BaseScriptItem, extra="allow"):
    from_ref: UniqueLabel = Field(None, description="Label of reference asset to inherit traits from")

class AssetsScript(BaseScriptItem):
    asset_kind: ClassName = Field(..., alias="asset_kind")
    assets: list[AssetScriptItem] | dict[UniqueLabel, AssetScriptItem] = None
