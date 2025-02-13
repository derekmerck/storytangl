from typing import TypeVar, Generic

from tangl.business.core import SingletonNode
from tangl.business.core import Associating
from .asset import Asset

AssetT = TypeVar('AssetT', bound=Asset)

class DiscreteAsset(Associating, SingletonNode[Asset], Generic[AssetT]):
    ...
