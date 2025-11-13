from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Generic, Optional, Type, TypeVar

from tangl.core.graph.node import Node
from tangl.core.graph.singleton_node import SingletonNode

from .asset_type import AssetType

# todo: how do we handle owned nodes?  These are resources associated with another resource
Associating = object

AssetT = TypeVar("AssetT", bound=AssetType)


class DiscreteAsset(SingletonNode[AssetT], Generic[AssetT]):
    """
    Graph node wrapper for discrete asset singletons.

    Each instance represents a specific manifestation of an asset type
    in the story graph, with its own state and relationships.

    Example
    -------
    ::

        class Weapon(AssetType):
            damage: int = 10

        Weapon(label='iron_sword', damage=15)

        # Create typed wrapper
        Sword = DiscreteAsset[Weapon]
        my_sword = Sword(label='iron_sword', graph=story_graph)

        # Delegates to singleton
        assert my_sword.damage == 15

        # Instance state
        my_sword.owner_id = player.uid
        my_sword.acquired_at = datetime.now()
    """

    wrapped_cls: ClassVar[Type[AssetType]] = AssetType

    # Instance variables (not on singleton)
    owner_id: Optional[str] = None
    """UID of the node that owns this asset."""

    location: Optional[str] = None
    """Current location/container for this asset."""

    acquired_at: Optional[datetime] = None
    """When this asset was obtained."""

    @classmethod
    def __class_getitem__(cls, wrapped_cls: Type[AssetT]) -> type[DiscreteAsset[AssetT]]:
        if isinstance(wrapped_cls, TypeVar):
            if wrapped_cls.__bound__ is None:
                raise TypeError("Type variables used with DiscreteAsset must be bound to AssetType.")
            wrapped_cls = wrapped_cls.__bound__
        if not isinstance(wrapped_cls, type) or not issubclass(wrapped_cls, AssetType):
            raise TypeError("DiscreteAsset wrappers must be bound to AssetType subclasses.")
        return super().__class_getitem__(wrapped_cls)



class HasDiscreteAssets(Node):

    @property
    def assets(self) -> list[DiscreteAsset]:
        # todo: need functions for assigning and tracking these pseudo dependencies
        return self.find_associates(has_cls=DiscreteAsset)
