"""
Outfits connect Singleton Wearable objects to an Actor node or Player proxy.

The outfit state handler can check whether items or regions accessible for visibility or interactions.  It provides an outer-to-inner sorted list of visible wearables to the outfit renderer, and validates and provides state transitions for individual wearable objects.  Methods such as "put_on(wearable)" are delegated by the outfit to the state handler.

Wearable has a description conditioned on the current state.  "A pair of blue jeans" or "an open jacket".  Outfit uses these descriptions to generate its own prosaic description of the _visible_ elements of the outfit.  "She is wearing a pair of blue jeans and a jacket."  We can't see that she is also wearing a t-shirt under the jacket, b/c the jacket is closed.  If it were open, we could see the t-shirt though.

Wearables and Outfits are designed to be comprehensively usable as is, but also to be very flexible, so they can be subclassed to provide additional functions, for example, Tearable or HasPockets.
"""

from __future__ import annotations
from typing import Iterable

from pydantic import BaseModel, model_validator
import logging

from tangl.type_hints import UniqueLabel
from tangl.lang.helpers import oxford_join
# from tangl.entity import BaseEntityHandler
# from tangl.core import on_render, Renderable
# from tangl.story.story_node import StoryNode
from tangl.lang.body_parts import BodyPart
from tangl.mechanics.presence.wearable.enums import WearableState, WearableLayer
from tangl.mechanics.presence.wearable import Wearable

logger = logging.getLogger(__name__)


class OutfitHandler:
    """
    This class encapsulates the logic for determining the visibility and accessibility of
    wearables within an outfit, the state transitions that can occur, and the addition/removal
    of items from the outfit.
    """

    @classmethod
    def _normalize_wearable_arg(cls, outfit: OutfitManager, ww: str | Wearable):
        if isinstance(ww, Wearable):
            return ww
        elif isinstance(ww, UniqueLabel):
            res = filter(lambda x: x.label == ww, outfit.wearables)
            res = list(res)
            if res:
                return res[0]
        raise TypeError(f"Unknown wearable argument {ww}")

    @classmethod
    def validate_outfit(cls, *wearables: Wearable) -> bool:
        """Guarantee that the outfit is non-overlapping on each layer"""
        return True

    @classmethod
    def describe(cls, outfit: OutfitManager) -> str:
        """
        >>> outfit.describe()
        He is wearing a dark jacket and blue jeans.
        >>> outfit.open('jacket')
        >>> outfit.describe()
        He is wearing a dark jacket and blue jeans.  His dark jacket is open,
        revealing a t-shirt underneath.
        >>> outfit.describe()
        He is wearing an open jacket, a light t-shirt, and blue jeans.
        """

        descriptions = []
        for wearable in cls.get_visible_items(outfit):
            r = WearableHandler.render_desc(wearable)
            descriptions.append(r)
        return oxford_join(descriptions)

    @classmethod
    def _covered_by(cls, outfit: OutfitManager,
                    target_wearable: Wearable,
                    covering_states: list[WearableState]):
        target_wearable = cls._normalize_wearable_arg(outfit, target_wearable)
        for wearable in outfit.wearables:
            # Ignore self
            if wearable is target_wearable:
                continue
            # If any wearable on the same or a higher layer covers any of the same regions and is in a covering state, the target_wearable is covered
            if wearable.layer >= target_wearable.layer and wearable.covers & target_wearable.covers and \
                    wearable.state in covering_states:
                logger.debug(f"{target_wearable} clobbered by {wearable}")
                return False
        return True


    @classmethod
    def is_visible(cls, outfit: OutfitManager, target_wearable: Wearable) -> bool:
        """
        Determines if a `Wearable` is visible within the `Outfit`.
        (Any covering item is OPEN or OFF)

        Parameters
        ----------
        target_wearable : Wearable
            The `Wearable` to check for visibility.

        Returns
        -------
        bool
            True if the `Wearable` is visible, False otherwise.
        """
        target_wearable = cls._normalize_wearable_arg(outfit, target_wearable)
        return cls._covered_by(outfit, target_wearable, [WearableState.ON])

    @classmethod
    def is_accessible(cls, outfit: OutfitManager, target_wearable: Wearable) -> bool:
        """
        Determines if a `Wearable` is accessible for adding or removing within the `Outfit`.
        (Any covering item is OFF)

        Parameters
        ----------
        target_wearable : Wearable
            The `Wearable` to check for accessibility.

        Returns
        -------
        bool
            True if the `Wearable` is accessible, False otherwise.
        """
        target_wearable = cls._normalize_wearable_arg(outfit, target_wearable)
        return cls._covered_by(outfit, target_wearable, [WearableState.ON, WearableState.OPEN])

    @classmethod
    def get_visible_items(cls, outfit: OutfitManager) -> list[Wearable]:
        """
        Retrieves the list of visible `Wearable` items within the `Outfit`.

        The list is sorted by region and layer, from the outermost layer to the innermost layer.

        Returns
        -------
        list[Wearable]
            The list of visible `Wearable` items.
        """
        return [ ww for ww in outfit.wearables if cls.is_visible(outfit, ww) ]

    @classmethod
    def can_transition(cls, outfit: OutfitManager, wearable: Wearable, to_state: WearableState) -> bool:
        wearable = cls._normalize_wearable_arg(outfit, wearable)
        if wearable not in outfit.wearables:
            # Not allowed to _add_ or _remove_ items as a state transition
            logger.debug(f"{wearable} not in wearables")
            return False
        if not cls.is_visible(outfit, wearable):
            logger.debug(f"{wearable} not accessible")
            return False
        if not WearableHandler.can_transition(wearable, to_state):
            return False
        return True

    @classmethod
    def transition(cls, outfit: OutfitManager,
                   wearable: Wearable,
                   to_state: WearableState):

        wearable = cls._normalize_wearable_arg(outfit, wearable)

        if cls.can_transition(outfit, wearable, to_state):
            wearable.state = to_state

        elif wearable not in outfit.wearables:
            raise ValueError(f"Cannot add an item {wearable} as a transition change")
        else:
            raise ValueError(f"Cannot transition '{wearable.text}' from {wearable.state} to {to_state}")


class HasOutfit:

    glasses: bool = False
    outfit_type: str = None
    outfit_kws: str = None
    outfit_palette: str = None

    @property
    def wearables(self: StoryNode) -> Iterable[Wearable]:
        res = self.find_children(Wearable)
        return sorted(res, key=lambda ww: ww.layer, reverse=True)

    @property
    def outfit(self) -> OutfitManager:
        return OutfitManager(self)

    @on_render.register()
    def _provide_outfit_description(self):
        return {'outfit': self.outfit.render_desc()}


class OutfitManager:
    """
    Wearables may be assigned to Actors and cover BodyParts through an outfit manager.

    actor.outfit.put_on(pants)
    """

    def __init__(self, node: HasOutfit):
        self.node = node
        super().__init__()
        if not OutfitHandler.validate_outfit(*self.wearables):
            raise ValueError("Improperly configured outfit")

    @property
    def wearables(self) -> Iterable[Wearable]:
        return self.node.wearables

    def _wearables_by_label(self):
        return { w.label: w for w in self.wearables }

    def __getattr__(self, item):
        if value := self._wearables_by_label().get(item):
            return value
        return super().__getattr__(item)

    # --------------------
    # Concept Api

    def describe(self) -> str:
        return OutfitHandler.describe(self)

    def adapt_media_spec(self) -> MediaSpec:
        ...

    # --------------------
    # Public Api

    def can_put_on(self, wearable: Wearable) -> bool:
        return OutfitHandler.can_transition(self, wearable, WearableState.ON)

    def put_on(self, wearable: Wearable):
        return OutfitHandler.transition(self, wearable, WearableState.ON)

    def can_take_off(self, wearable: Wearable) -> bool:
        return OutfitHandler.can_transition(self, wearable, WearableState.OFF)

    def take_off(self, wearable: Wearable):
        return OutfitHandler.transition(self, wearable, WearableState.OFF)

    def can_open(self, wearable: Wearable) -> bool:
        return OutfitHandler.can_transition(self, wearable, WearableState.OPEN)

    def open(self, wearable: Wearable):
        return OutfitHandler.transition(self, wearable, WearableState.OPEN)

    # Transition to 'on' is called 'close' if wearable is open
    def can_close(self, wearable: Wearable) -> bool:
        return wearable.state is WearableState.OPEN and OutfitHandler.can_transition(self, wearable, WearableState.ON)

    def close(self, wearable: Wearable):
        return wearable.state is WearableState.OPEN and OutfitHandler.transition(self, wearable, WearableState.ON)

