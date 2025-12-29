
from __future__ import annotations
from typing import Protocol, MutableMapping, TypedDict
from enum import Enum
from uuid import UUID

# Response types are enumerated with `pydantic` in `tangl.models`,
# they are simplified here so the protocol spec is self-contained.

Uid = str | UUID
class NodeResponse(TypedDict):
    uid: Uid
    text: str
class BlockResponse(NodeResponse):
    actions: list[NodeResponse]
    media: list[NodeResponse]
StoryResponse = list[BlockResponse]  #: current list of block responses
StatusResponse = list[dict]          #: list of kv attributes with formatting
InfoResponse = dict                  #: dict of information about an object
MediaData = bytes | str
RuntimeStatement = str

class Singletons(Protocol):
    uid: Uid
    def instance(cls, uid) -> Singletons: ...
    def __reduce__(self) -> tuple: ...
    # Singletons are not serializable to dict; `__reduce__` references and dereferences the Singleton instance

class World(Singletons, Protocol):
    """
    A world is a collection of story templates and hooks that is in charge of
    instantiating new stories from templates and managing story object lifecycle
    hooks.
    There are relatively few worlds to be managed, and they are static after
    initialization, so they are implemented using a Singleton pattern.
    """
    uid: Uid
    templates: dict[Uid, dict]  #: story node templates for instantiating a new stor
    pm: 'PluginManager'         #: `pluggy` hooks for story objects referencing this world
    def ns(self) -> dict:
        """Cascading namespace for runtime calcs, includes static, story-independent variables"""
        ...
    def create_story(self, *args, user: User = None, **kwargs) -> Story:
        """Instantiate a set of scenes, blocks, and other story nodes based on world templates"""
        ...
    def get_media(self, media_type: Enum, media_id: Uid) -> MediaData:
        """Story-independent media by type and id"""
        ...
    def get_info(self) -> InfoResponse:
        """Dictionary of public information about this world and ui/branding data"""
        ...

class Serializable(Protocol):
    """
    Serializable objects can interact with the data layer.  Simplest is just to
    ensure the default 'reduce' behavior works and rely on Python's pickle.
    Other backends may rely on more sophisticated serialization/deserialization
    using the to_dict and from_dict methods.
    """
    def to_dict(self, **kwargs) -> dict: ...  # for serialization, also to_yaml, to_json, to_bson
    @classmethod
    def from_dict(cls, **kwargs) -> StoryNode: ...  # for deserialization, also from_yaml, from_json, from_bson
    def __reduce__(self) -> tuple: ...

class User(Serializable, Protocol):
    """
    A User represents an entity that owns a collection of stories.

    **Security**: Users are indexed by hashing their "secret", a short phrase.
    Secret-hash indexing is not intended to provide security, authentication, or
    even guaranteed uniqueness. It serves as a self-selected identifier.
    The current project design only supports multiple users minimally, primarily
    for a public reference server, and does not include formal authentication.
    _However_, for a small population of users with unique secrets, secret-hash
    indexing can help obscure user accounts from each other, making exhaustive
    searches for valid user keys more difficult.
    """
    uid: Uid      #: unique id based on hashing the secret
    secret: str   #: user selected secret
    #: indicates which story-world the user is currently interacting with to the story manager
    current_world: World
    story_metadata: dict[Uid, dict]  #: metadata for each story, play-throughs, achievements, etc.
    def ns(self) -> dict:
        """Cascading namespace for runtime calcs, includes story medata for all stories"""
        ...
    def get_info(self) -> InfoResponse: ...

class StoryNode(Serializable, Protocol):
    """
    Basic unit of story organization, they can be augmented by mixin classes for rendering,
    runtime evals and execs, checking conditions, traversing a graph, and owning
    other nodes.

    Story nodes are subclassed to represent intuitive narrative features like `Scenes`
    (tree roots), `Blocks` (narrative beats), `Actions` (verbs/branching choices), `Actors`
    (npcs), and `Assets` (nouns/objects).

    Certain story node subclasses may carry other specialized handlers, such as `Challenge
    Blocks`, which wrap an interactive game handler that provides for more complex interactions.

    Story nodes may also have various media handlers for image or audio.  Media handlers
    manage static media assets or generate dynamic assets as required (such as `svg`
    'paperdoll' avatars or AI-generated images).
    """
    uid: Uid
    path: str                  #: path to this node from the index, unique, human-readable
    parent: StoryNode | None   #: StoryNodes are organized in trees (scenes) and collections (stories)
    children: list[StoryNode]
    index: Story               #: each node is indexed in a single story
    tags: list[str | Enum]       #: a set of 'tags' for this node
    locals: dict               #: local vars that cascade to this node's children
    def ns(self) -> dict:
        """Cascading namespace for runtime calcs, includes local variables and subclass-specific elements like game handlers, links to parent namespace or story namespace if it is a root"""
        ...
    def get_info(self) -> InfoResponse: ...

class Traversable:
    """A collection of mixin functions and handlers"""
    def lock(self): ...                 #: lock the node for traversal
    def unlock(self, force=False): ...  #: unlock the node, optionally force unlock dependencies
    conditions: list[RuntimeStatement]  #: availability runtime conditions
    def avail(self) -> bool: ...        #: unlocked and availability conditions satisfied
    effects: list[RuntimeStatement]     #: runtime effects to apply on traversal
    def apply(self):  ...
    def enter(self) -> StoryNode: ...   #: apply effects, render output, optionally redirect
    def exit(self) -> StoryNode: ...    #: identify the next node in the traversal
    runtime_handler: 'Handler'

class Scene(Traversable, StoryNode):
    """The root of a narrative tree, a collection of blocks and roles"""
    def blocks(self) -> list[Block]: ...
    def roles(self) -> list[Role]: ...

class Block(Traversable, StoryNode):
    """A narrative beat, renders text and generates actions/choices based on current game state"""
    def render(self) -> dict: ...
    def images(self) -> MediaData: ...
    def voice(self) -> MediaData: ...
    actions: list[Action]
    render_handler: 'Handler'
    image_handler: 'Handler'
    voice_handler: 'Handler'

class Challenge(Block):
    game_handler: 'Handler'

class Action(Traversable, StoryNode):
    """A narrative choice, leading to the next block"""
    def render(self) -> dict: ...
    target_block_id: Uid
    render_handler: 'Handler'

class Role(StoryNode):
    """Placeholder for the actor assigned to specific roles in a scene."""
    actor: Actor
    actor_template: dict          # create a new actor to spec
    actor_reference_id: Uid       # use an existing actor
    actor_conditions: list[RuntimeStatement]  # find an existing actor with spec
    def cast(self) -> bool: ...   # assign self.actor based on rules

class Extras(Role):
    """Role for auto-generated generic NPCs"""
    count: int                    # number of generic actors to create

class Actor(StoryNode):
    """Represents a story NPC that maintains state throughout the story"""
    name: str
    gender: Enum
    desc: str
    outfit: set[Asset]  #: Wearables

class Asset(Singletons, StoryNode):
    """Represents a discrete noun in the narrative, immutable and shared,
    implemented with a modified Singleton pattern.

    Uses 'instance inheritance' to create objects that refer-to and
    override other objects, such as a 'blue shirt' that inherits from 'shirt'
    with the color 'blue'.

    Common asset types are Fungibles (tradeable currencies), Badges (carrying
    effects and tags), Wearables (clothes)"""
    ...

class Story(Serializable, Protocol):
    """
    An indexed collection of story nodes.  It provides centralized organization
    for navigating scene trees and tracking state.
    """
    uid: Uid
    world: World                 #: created by a single world from templates
    user: User                   #: owned by a single user
    nodes: dict[Uid, StoryNode]  #: index of story objects and trees in this story
    current_block: StoryNode     #: currently entered node
    def ns(self) -> dict:
        """cascading namespace for runtime calcs, includes index of nodes by path and links to world and user namespaces"""
        ...
    def add_node(self, node: StoryNode): ...
    def find(self, node_id: Uid) -> StoryNode: ...
    def filter(self, filter_fn: callable) -> list[StoryNode]: ...
    def get_info(self) -> InfoResponse: ...  #: info about this story's user, world, node uid's, etc.

class StoryApi(Protocol):
    """
    Service layer wrapper for a single story, providing a limited client interface.

    **Concurrency**: Three api calls, `do_action`, `goto_node`, and `apply_effect`,
    may mutate the story state. These require a read/write open-story context when
    called from the story manager, which in turn must be locked if calling from an
    asynchronous method.
    """
    story: Story
    # Client interface
    def get_update(self, **kwargs) -> StoryResponse: ...  #: return current story update
    def do_action(self, action: Uid | StoryNode, **kwargs) -> StoryResponse: ...  #: generate a story update based on choice
    def get_status(self) -> StatusResponse: ...  #: list of keys, different from `get_info`
    def get_media(self, media_type: Enum, media_id: Uid) -> MediaData: ...  #: story-dependent media by type and id
    # Developer interface
    def goto_node(self, node: Uid | StoryNode ) -> StoryResponse: ...     #: force current node and update
    def get_node_info(self, node: Uid | StoryNode ) -> InfoResponse: ...  #: alias for find/get_info
    def check_expr(self, expr: str): ...    #: eval expr in story ns ie, `player.gold >= 100`
    def apply_effect(self, expr: str): ...  #: exec expr in story ns ie, `player.gold = 100`

class StorageBackend(MutableMapping):
    """
    Data layer, StorageBackend wraps various flavors of persistent and non-persistent
    storage, such as in-memory, pickle and yaml files, and redis or bson databases.
    It presents as a MutableMapping.
    """
    pass

class StoryManager(Protocol):
    """
    The StoryManager's basic purpose is to access Story and User objects and
    yield StoryApi instances.  It organizes interactions between the service
    layer apis, the domain layer story and user objects, and the data layer.

    **Concurrency**: The 'open story' context needs to be locked for atomicity
    when opened as read-write inside an asynchronous function like a FastApi
    endpoint.
    """
    storage: MutableMapping
    def put_story(self, story: Story): ...
    def get_story(self, user_id: Uid = None, world_id: Uid = None) -> Story: ...
    def remove_story(self, user_id: Uid = None, world_id: Uid = None): ...
    def put_user(self, user: User): ...
    def get_user(self, user_id: Uid) -> User: ...
    def remove_user(self, user_id: Uid): ...
    def open_story(self, user_id: Uid, world_id: Uid, write_back=False) -> StoryApi: ...
    def update_user(self, user_id: Uid, secret: str = None, current_world: World = None, **kwargs) -> User: ...

class StoryManagerApi(Protocol):
    """
    Service layer wrapper for a story manager, providing a limited interface that
    delegates api calls onto to the underlying story objects. Presentation-layer
    clients and servers can use the service api to specify stories and execute
    api methods or get data on them.

    **Concurrency**: The`do_story_action`, `goto_story_node`, `apply_story_effect`,
    use a read-write story manager context, so they should be locked for atomicity
    when used in an asynchronous context.  `create`, `drop`, and `update` functions
    should also be locked for their duration.

    **Clients**: The package includes a `FastApi` REST endpoint server and `cmd2`
    interactive cli that use the story manager api to interact the game logic.
    """
    story_manager: StoryManager

    # Story Client interface
    def get_story_update(self, **identifiers) -> StoryResponse: ...
    def do_story_action(self, action: Uid, **identifiers) -> StoryResponse: ...
    def get_story_status(self, **identifiers) -> StatusResponse: ...
    def get_story_media(self, media_type: str, media_id: Uid, **identifiers) -> MediaData: ...

    # Story Developer interface
    def goto_story_node(self, node: Uid, **identifiers) -> StoryResponse: ...
    def get_story_node_info(self, node: Uid, **identifiers) -> InfoResponse: ...
    def check_story_expr(self, expr: str, **identifiers) -> bool: ...
    def apply_story_effect(self, expr: str, **identifiers) -> bool: ...

    # User Account interface
    def create_story(self, user_id: Uid, world_id: Uid) -> StoryResponse: ...
    def drop_story(self, user_id: Uid, world_id: Uid): ...

    def create_user(self, secret: str) -> tuple[Uid, str]: ...
    def get_user_info(self, user_id: Uid) -> InfoResponse: ...
    def update_user_secret(self, user_id: Uid, secret: str) -> tuple[Uid, str]: ...
    def update_user_current_world(self, user_id: Uid, world_id: Uid): ...
    def drop_user(self, user_id: Uid): ...

class WorldApi(Protocol):
    # World Public interface
    @staticmethod
    def get_world_info(world_id: Uid) -> InfoResponse: ...
    @staticmethod
    def get_world_media(world_id: Uid, media_type: str, media_id: Uid) -> MediaData: ...
    # World Developer interface
    @staticmethod
    def get_world_scenes(world_id: Uid) -> InfoResponse: ...

class SystemApi(Protocol):
    # System Public interface
    @staticmethod
    def get_system_info() -> InfoResponse: ...
    @staticmethod
    def get_key_for_secret(secret: str) -> tuple[Uid, str]: ...
    # System Developer interface
    @staticmethod
    def reset_system(hard: bool): ...
