from typing import TypeVar, Generic, ClassVar, Type

from tangl.core.entity import SingletonNode, Node
# from tangl.core import Associating
from .asset_type import AssetType

# todo: how do we handle owned nodes?  These are resources associated with another resource
Associating = object

AssetT = TypeVar('AssetT', bound=AssetType)

class DiscreteAsset(SingletonNode[AssetT], Generic[AssetT]):
    """
    Assets are singleton "wrappers", derived from AssetTypes.  They are proper
    story nodes with instance variables that can be linked into a story graph through
    parenting or association.

    Assets can be created using SingletonNode's Generic interface, i.e.
    Asset[Shirt] or Asset[Pants]

    Assets are ownable and tradeable via the TradeHandler and Tradeable mixin.
    """
    wrapped_cls: ClassVar[Type[AssetT]] = None



class HasDiscreteAssets(Node):

    @property
    def assets(self) -> list[DiscreteAsset]:
        # todo: need functions for assigning and tracking these pseudo dependencies
        return self.find_associates(has_cls=DiscreteAsset)
