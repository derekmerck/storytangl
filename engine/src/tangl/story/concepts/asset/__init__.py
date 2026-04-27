"""Story asset vocabulary.

Assets are story concepts, not a separate inventory engine. ``AssetType`` gives
tokenizable objects a shared singleton base, ``CountableAsset`` names fungible
resources, and ``AssetWallet`` stores fungible counts.
"""

from __future__ import annotations

from .asset_type import AssetType, CountableAsset, Fungible
from .holder import HasAssets
from .transaction import AssetTransactionManager, AssetTransactionResult
from .wallet import AssetWallet

__all__ = [
    "AssetType",
    "AssetTransactionManager",
    "AssetTransactionResult",
    "AssetWallet",
    "CountableAsset",
    "Fungible",
    "HasAssets",
]
