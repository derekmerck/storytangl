"""Story asset vocabulary.

Assets are story concepts, not a separate inventory engine. ``AssetType`` gives
tokenizable objects a shared singleton base, ``CountableAsset`` names fungible
resources, and ``AssetWallet`` stores fungible counts.
"""

from .asset_type import AssetType, CountableAsset, Fungible
from .wallet import AssetWallet

__all__ = [
    "AssetType",
    "AssetWallet",
    "CountableAsset",
    "Fungible",
]
