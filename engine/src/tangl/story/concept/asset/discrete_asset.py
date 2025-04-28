from typing import TypeVar, Generic

from tangl.core.graph import SingletonNode, Node
from tangl.core import Associating
from .asset import Asset

AssetT = TypeVar('AssetT', bound=Asset)

class DiscreteAsset(Associating, SingletonNode[Asset], Generic[AssetT]):
    ...


class HasDiscreteAssets(Node):

    @property
    def assets(self) -> list[DiscreteAsset]:
        return self.find_children(has_cls=DiscreteAsset)
