from typing import TypeVar, Generic, ClassVar, Type

from tangl.core.graph import SingletonNode, Node
from tangl.core import Associating
from .asset_type import AssetType

AssetT = TypeVar('AssetT', bound=AssetType)

class DiscreteAsset(Associating, SingletonNode, Generic[AssetT]):
    """
    Assets are singleton "wrappers", derived from AssetTypes.  They are proper
    story nodes with instance variables that can be linked into a story graph through
    parenting or association.

    Assets can be created using SingletonNode's Generic interface, i.e.
    Asset[Shirt] or Asset[Pants]

    Assets are ownable and tradeable via the TradeHandler and Tradeable mixin.
    """
    wrapped_cls: ClassVar[Type[AssetType]] = AssetT


class HasDiscreteAssets(Node):

    @property
    def assets(self) -> list[DiscreteAsset]:
        return self.find_children(has_cls=DiscreteAsset)
