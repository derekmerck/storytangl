from __future__ import annotations
from collections import Counter
from typing import TYPE_CHECKING, Optional, Iterable, Union, TypeVar, Generic, Literal, Any

from pydantic import BaseModel

from tangl.type_hints import Identifier, StringMap
from .entity import HasConditions, HasEffects, Singleton, TaskHandler, TextFragment
from .graph import NodeMixin, VisitableNode, TransitEdge, DynamicEdge, HasAssociates, HasDynamicAssociates, DynamicallyAssociatingEntity, WrappedSingletonNode
from .story import Story, StoryId

if TYPE_CHECKING:
    from .user import UserId
    from .world import WorldId, World

# ----------------
# StoryNode
# ----------------
class StoryNode(HasConditions, HasEffects, NodeMixin):
    @property
    def story(self) -> Story: ...  # alias to self.graph
    @property
    def world(self) -> World: ...  # alias to self.story.world

# ----------------
# StoryNode Info
# ----------------
class StoryNodeInfo(BaseModel, allow_extra=True):
    story_id: StoryId
    user_id: UserId
    world_id: WorldId
    node_id: Identifier
    label: str
    tags: list[str] = None
    # include conditions, effects, renderable properties, locals, visited, locked, etc.
    locals: StringMap = None
    text: Optional[str] = None

# ----------------
# Visitable StoryNodes
# ----------------
class Scene(StoryNode, VisitableNode):
    # Story-related objects included in local context
    roles: Iterable[Role]
    locations: Iterable[Location]
    blocks: Iterable[Block]
    assets: Iterable[DiscreteAsset]

class Block(StoryNode, VisitableNode): ...
class Choice(StoryNode, TransitEdge): ...

class ChoiceFragment(TextFragment):
    choice_id: Identifier
    choice_payload: StringMap = None
    active: bool = True

# ----------------
# Dynamic StoryNodes - Actors, Places
# ----------------
# alias successor_identifier -> actor_id, etc.
class Actor(StoryNode):
    name: str
    roles: Iterable[Role]
class Role(DynamicEdge[Actor]): ...

# alias successor_identifier -> place_id, etc.
class Place(StoryNode):
    name: str
    locations: Iterable[Location]
class Location(DynamicEdge[Place]): ...

# ----------------
# Static StoryNodes - Discrete and Fungible Assets
# ----------------

# Assets are based on a world-specific Singleton concept
# - the singleton itself can be referenced by the owner as a non-parented child
# - the singleton can be wrapped in a node and associated with the owner (made discrete)
# - the singleton can be accessed via a counter wallet on the owner (made fungible)
#
# Referenced singleton assets may also have dynamic assignment/unassignment conditions/criteria
# i.e., health = 0, the Disabled asset attaches and donates an 'is_disabled' tag to the owner,
# it may only be detached as an effect of visiting a doctor, for example.

class AssetType(Singleton):
    name: str
class DiscreteAsset(StoryNode, WrappedSingletonNode[AssetType]): ...

StoryNodeMixin = StoryNode

class HasDiscreteAssets(HasAssociates[AssetType], StoryNodeMixin):
    assets: list[DiscreteAsset]  # children

    def can_gain(self, asset: DiscreteAsset) -> bool: ...
    def can_lose(self, asset: DiscreteAsset) -> bool: ...
    def gain(self, asset: DiscreteAsset) -> float: ...
    def lose(self, asset: DiscreteAsset) -> float: ...

DiscreteAssetHandler = TaskHandler

AT = TypeVar('AT', bound=AssetType)   # Fungible asset type

class HasFungibles(StoryNodeMixin, Generic[AT]):
    wallet: Counter[AT]
    def can_gain_some(self, which: AT, amount: float) -> bool: ...
    def can_lose_some(self, which: AT, amount: float) -> bool: ...
    def gain_some(self, which: AT, amount: float): ...
    def lose_some(self, which: AT, amount: float): ...

class FungibleAsset(AssetType):
    value: int

FungibleAssetHandler = TaskHandler

class HasFungibleAssets(HasFungibles[FungibleAsset]):
    def total_value(self) -> float: ...

class DynamicAsset(DynamicallyAssociatingEntity, AssetType):
    # Singleton that can attach and detach automatically, use with 'DonatesContext'
    # to dynamically add and remove tags like a badge.
    ...

class HasDynamicAssets(StoryNodeMixin, HasDynamicAssociates):
    def update_dynamic_assets(self):
        ...

Asset = Union[AssetType, DiscreteAsset, FungibleAsset, DynamicAsset]
HasAssets = Union[HasFungibleAssets, HasFungibleAssets, HasDynamicAssets]

class TradeManager(FungibleAssetHandler, DiscreteAssetHandler):
    sender: HasAssets
    receiver: HasAssets

    def trade(self, send: Asset, receive: Asset, send_amount=None, receive_amount=None): ...
