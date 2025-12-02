from __future__ import annotations
import functools
from enum import Enum
from typing import ClassVar, Optional
import logging

from pydantic import Field, field_validator, ValidationInfo, field_serializer

from tangl.utils.enum_plus import EnumPlusMixin
from tangl.lang.helpers.pattern import is_plural
from tangl.lang.body_parts import BodyRegion
from tangl.core.graph import SingletonNode
from tangl.story.concepts.asset import AssetType
from .enums import WearableLayer, WearableState

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# class BodyRegion(EnumPlusMixin, Enum):
#     # this is in body-region now
#     HEAD = "head"
#     UPPER = TOP = "upper"
#     LOWER = BOTTOM = "lower"
#     HANDS = "hands"
#     FEET = "feet"
#


class WearableHandler:
    """
    A handler for managing the current state and description of a `Wearable`.

    Wearables have `layer` and `covers` attributes.  `covers` is a set of enums of Body Region, for example, TOP (shirts) and BOTTOM (pants).  `layer` is an enum of clothing layers, for example, INNER and OUTER.  Covers is a set because a single wearable can cover multiple body parts, for example, a dress covers both TOP and BOTTOM regions.

    These enum classes may be changed as needed to provide additional features, like adding a HEAD region for hats or an OPEN state for jackets.
    """

    state_transitions: ClassVar[dict] = {
        WearableState.OFF: {WearableState.ON},
        WearableState.ON: {WearableState.OFF, WearableState.OPEN},
        WearableState.OPEN: {WearableState.ON, WearableState.OFF}
    }

    @classmethod
    def can_transition(cls, wearable: Wearable, to_state: WearableState):
        if to_state in wearable.disallowed_states:
            # Not allowed to use wearable that way
            logger.debug(f"{wearable.text} {to_state} is disallowed")
            return False
        return to_state in cls.state_transitions[wearable.state]

    @classmethod
    def transition(cls, wearable: Wearable, to_state: WearableState):
        if not cls.can_transition(wearable, to_state):
            raise ValueError(f"Not allowed to transition to {to_state}")
        wearable.state = to_state

    @classmethod
    def render_desc(cls, wearable: Wearable) -> str:
        return wearable.noun


class WearableType(AssetType):
    """
    Wearables are Singleton Asset-type objects.  They are managed through a
    complementary "Outfit" class that can be attached to an Actor or Player Proxy.

    Set `locals.exclusive = True` or add the 'exclusive' tag to the object to
    indicate that the item is exclusive to a particular role or actor.
    """
    # todo: Mix-in the 'Nominal' class, so they render as a noun phrase.
    #       that would include `is_plural` as well

    _instances: ClassVar[dict[str, WearableType]]

    noun: str = Field(None, validate_default=True)

    @field_validator('noun', mode="before")
    @classmethod
    def _set_default_noun(cls, data: str, info: ValidationInfo):
        if data is None:
            label = info.data['label']
            return label
        return data

    plural: bool = Field(None, validate_default=True)  # i.e., some pants

    @field_validator('plural', mode="before")
    @classmethod
    def _set_default_plural(cls, data: bool, info: ValidationInfo):
        logger.debug(f'checking plural, data={data}')
        if data is None:
            noun = info.data['noun']
            return is_plural(noun)
        return data

    covers: set[BodyRegion] = Field(default_factory=set)
    layer: WearableLayer = WearableLayer.OUTER
    disallowed_states: set[WearableState] = Field(default_factory=set)
    adj: Optional[set[str]] = None
    color: Optional[str] = None

    @field_serializer('layer')
    def _use_enum_utils(self, value):
        return repr(value)

    state: WearableState = Field(WearableState.ON,
                                 json_schema_extra={'instance_var': True})   # e.g., on, off, open
    # condition: WearableCondition = Field(WearableCondition.NEW,
    #                                      json_schema_extra={'instance_var': True})
    # int or int-like, e.g., Quality

    # Any instance methods for wrappers need to be disguised as class methods, so they
    # can be rebound to the instance in the accessor
    @classmethod
    def is_exclusive(cls, self: Wearable):
        # Unfortunately, this can't be a property b/c it is a singleton method
        return self.has_tags('exclusive') or self.locals.get('exclusive', False)

    @classmethod
    def can_transition(cls, self: Wearable, to_state: WearableState):
        return WearableHandler.can_transition(self, to_state)

    @classmethod
    def transition(cls, self: Wearable, to_state: WearableState):
        return WearableHandler.transition(self, to_state)

    @classmethod
    def render_desc(cls, self: Wearable):
        return WearableHandler.render_desc(self)

    @classmethod
    def load_defaults(cls, *args, **kwargs):
        super().load_instances_from_yaml("tangl.mechanics.presence.wearable", "wearables.yaml")

WearableType.load_defaults()
Wearable = SingletonNode._create_wrapper_cls(WearableType, "Wearable")
