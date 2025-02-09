from collections import Counter

from tangl.business.story.asset.asset import Asset

class CountableAsset(Asset):
    ...


class AssetWallet(Counter[CountableAsset]):
    ...
