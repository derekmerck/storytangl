from typing import TypeVar, Generic, Type, ClassVar

from pydantic import field_validator

from tangl.story.concept.asset import Asset, DiscreteAsset
from tangl.narrative.lang.body_parts import BodyRegion
from .enums import WearableLayer

class WearableType(Asset):
    body_region: BodyRegion = BodyRegion.TOP     # hands, arms, upper, etc.
    layer: WearableLayer = WearableLayer.OUTER   # or int

    @classmethod
    def load_defaults(cls):
        cls.load_instances_from_yaml('tangl.mechanics.look.wearable', 'wearables.yaml')

WrappedWearable = TypeVar('WrappedWearable', bound=Asset)

class Wearable(Asset):
    wrapped_cls: ClassVar[Type[WearableType]] = WearableType

