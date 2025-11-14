"""Asset system for managing countable and discrete assets.

Why
===
Expose a curated import surface for asset primitives that inventory-capable nodes
use to manage story state.

Tier System
===========
#. Tags – boolean flags on :class:`tangl.core.entity.Entity` instances.
#. Inv – simple named items tracked via :attr:`tangl.core.Node.inv`.
#. Wallet – typed countable assets managed by :class:`.AssetWallet`.
#. Bag – discrete asset nodes wrapped by :class:`.AssetBag`.

Usage Examples
==============
Countable assets (wallet)
-------------------------
.. code-block:: python

   from tangl.story.concepts.asset import AssetWallet, CountableAsset

   class Currency(CountableAsset):
       'Simple fungible asset.'

   Currency(label="gold", value=1.0)

   wallet = AssetWallet()
   wallet.gain(gold=50)
   wallet.spend(gold=10)

Discrete assets (bag)
---------------------
.. code-block:: python

   from tangl.core import Graph, Node
   from tangl.story.concepts.asset import AssetBag, AssetType, DiscreteAsset, HasAssetBag

   class Player(Node, HasAssetBag):
       'Graph node with a discrete asset bag.'

   class Weapon(AssetType):
       damage: int = 10

   Weapon(label="sword", damage=15)

   graph = Graph(label="game")
   token = DiscreteAsset[Weapon](label="sword", graph=graph)

   player = Player(label="alice", graph=graph)
   player.bag.add(token)
"""

from .asset_type import AssetType
from .discrete_asset import DiscreteAsset
from .countable_asset import CountableAsset, Fungible
from .asset_wallet import AssetWallet, HasAssetWallet
from .asset_bag import AssetBag, HasAssetBag

__all__ = [
    # Types
    "AssetType",
    "DiscreteAsset",
    "CountableAsset",
    "Fungible",
    # Collections
    "AssetWallet",
    "AssetBag",
    # Mixins
    "HasAssetWallet",
    "HasAssetBag",
]
