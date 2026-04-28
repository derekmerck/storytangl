"""
.. currentmodule:: tangl.story.concepts

Story-domain entities that provide named providers and scoped dependency slots.

Conceptual layers
-----------------

1. :class:`Actor` and :class:`Location` are concrete providers that contribute
   symbols into render namespaces.
2. :class:`Role` and :class:`Setting` are dependency edges that bind those
   providers into scene and block scopes.
3. :class:`EntityKnowledge` and :class:`HasNarratorKnowledge` provide explicit
   narrator-facing epistemic bookkeeping on concept carriers.

Design intent
-------------
These types give story authors a domain vocabulary without changing the
mechanism-level provisioning rules in :mod:`tangl.vm`.
"""

from .actor import Actor
from .asset import AssetType, AssetWallet, CountableAsset, HasAssets
from .location import Location
from .narrator_knowledge import EntityKnowledge, HasNarratorKnowledge, get_narrator_key
from .role import Role
from .setting import Setting

__all__ = [
    "Actor",
    "AssetType",
    "AssetWallet",
    "CountableAsset",
    "EntityKnowledge",
    "HasAssets",
    "HasNarratorKnowledge",
    "Location",
    "Role",
    "Setting",
    "get_narrator_key",
]
