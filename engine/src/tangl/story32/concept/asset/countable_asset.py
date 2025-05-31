from collections import Counter

from pydantic import Field

from tangl.core import Entity
from .asset_type import AssetType

class CountableAsset(AssetType):
    ...


class AssetWallet(Counter[CountableAsset]):

    def total_value(self) -> float:
        return sum( [ k.value * v for k, v in self.items() ] )


class HasAssetWallet(Entity):

    wallet: Counter[CountableAsset] = Field(default_factory=AssetWallet)
