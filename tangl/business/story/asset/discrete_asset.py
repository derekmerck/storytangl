from typing import TypeVar, Generic

from tangl.core.graph import SingletonNode
from tangl.core.graph.handlers import Associating
from .asset import Asset

AssetT = TypeVar('AssetT', bound=Asset)

class DiscreteAsset(Associating, SingletonNode[Asset], Generic[AssetT]):
    ...
