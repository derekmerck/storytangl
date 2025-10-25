from typing import TypeVar, Generic, Type, ClassVar

from pydantic import field_validator

try:
    from tangl.story.concept.asset import AssetType, DiscreteAsset
except ImportError:
    AssetType = object
    DiscreteAsset = list
from tangl.lang.body_parts import BodyRegion
from .enums import WearableLayer

class WearableType(AssetType):
    body_region: BodyRegion = BodyRegion.TOP     # hands, arms, upper, etc.
    layer: WearableLayer = WearableLayer.OUTER   # or int

    @classmethod
    def load_defaults(cls):
        cls.load_instances_from_yaml('tangl.mechanics.look.wearable', 'wearables.yaml')


class Wearable(DiscreteAsset[WearableType]):

    wrapped_cls: ClassVar[Type[WearableType]] = WearableType

