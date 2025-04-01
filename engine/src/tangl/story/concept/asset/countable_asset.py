from collections import Counter

from pydantic import Field

from tangl.business.core import Entity
from .asset import Asset

class CountableAsset(Asset):
    ...


class AssetWallet(Counter[CountableAsset]):

    def total_value(self) -> float:
        return sum( [ k.value * v for k, v in self.items() ] )


class HasAssetWallet(Entity):

    wallet: AssetWallet = Field(default=AssetWallet)
