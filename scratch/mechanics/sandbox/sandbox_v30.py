"""
A SandboxScene is a specialized scene that contains a collection of SandboxNodes,
each with a schedule of  SandboxEvents, along with bookkeeping for the player's
current position and time.

When the player position cursor moves to a new sandbox node, enter will check for
available event redirects, and otherwise generate a default block including a
templated place description and a dynamically generated menu of place-specific event
actions, and connections to other nearby world places.

Place-specific and global conditional sandbox events are tested and may redirect
the logic to a different scene or block.  Those scenes will need to have a mechanism
to send the player back to the sandbox-scene to resume their journey.
"""
from __future__ import annotations
from typing import Optional, Literal

from pydantic import Field

from tangl.entity.mixins import AvailabilityHandler, NamespaceHandler
from tangl.graph import Node
from tangl.graph.mixins.traversal import TraversalHandler
from tangl.story.story import StoryNode
from tangl.story.concepts import Scene, Action
from tangl.story.concepts.actor import Role
from tangl.story.concepts.location import Location
from tangl.story.episode.menu import MenuActionHandler
from tangl.type_hints import Identifier, Tag, UniqueLabel
from tangl.exceptions import StoryAccessError

SandboxTime = int
# use whatever units you like, but be consistent
SandboxTimeDelta = int
# quick, short, medium, long, define as you like [0.1, 1.0, 6.0, 24.0]
SandboxTimeCondition = str

# For a grid sandbox
SandboxPosition = tuple[int, int]
SandboxPositionDelta = tuple[int, int]


class SandboxEventHandler:

    @classmethod
    def get_redirect_event(cls, node: HasSandboxEvents) -> Optional[SandboxEvent]:
        redirect_events = list(filter( lambda x: x.event_activation == "forced" and x.avail(), node.events ))
        if redirect_events:
            return redirect_events[0]

    @classmethod
    def get_selectable_events(cls, node: Node) -> list[Action]:
        selectable_events = list(filter( lambda x: x.event_activation == "selectable" and x.avail(), node.events ))
        return [ Action.from_node(event) for event in selectable_events ]

    @classmethod
    def increment_sb_time(cls, sandbox: Sandbox, sb_incr: SandboxTimeDelta):
        sandbox.sb_time += sb_incr
        cls.sb_update(sandbox)

    @classmethod
    def sb_update(cls, sandbox: Sandbox):
        # trigger scheduled progressions
        ...



class HasSandboxEvents:

    @property
    def events(self: Node) -> list[SandboxEvent]:
        return self.find_children(SandboxEvent)

    @TraversalHandler.enter_strategy
    def _check_for_event_redirect(self: Node, **kwargs) -> Optional[SandboxEvent]:
        return SandboxEventHandler.get_redirect_event(self)

    @MenuActionHandler.strategy
    def _include_selectable_events(self: Node, **kwargs) -> list[Action]:
        return SandboxEventHandler.get_selectable_events(self)


class SandboxAvailability:

    @property
    def sandbox(self: Node) -> Sandbox:
        node = self
        while not isinstance(node, Sandbox) and node.parent:
            node = node.parent
        return node

    @property
    def sb_time(self):
        return self.sandbox.sb_time

    req_tags: Tags = Field(default_factory=set)
    req_loc: UniqueLabel = None
    req_loc_tags: Tags = Field(default_factory=set)
    req_roles: UniqueLabel = None
    req_role_tags: Tags = Field(default_factory=set)
    req_schedule: SandboxTimeCondition = None

    @AvailabilityHandler.strategy
    def _has_req_tags(self):
        return [ f'player.has({self.req_tags})' ]

    @AvailabilityHandler.strategy
    def _has_req_loc(self):
        return [ f'{self.req_loc}.avail()',
                 f'{self.req_loc}.has({self.req_loc_tags}']

    @AvailabilityHandler.strategy
    def _has_req_roles(self):
        return [element for role in self.req_roles for element in
                (f'{role}.avail()', f'{role}.has({self.req_role_tags}')]

    @AvailabilityHandler.strategy
    def _meets_req_time_cond(self):
        # todo
        return []


EventActivationType = Optional[Literal['forced', 'selectable', 'never']]

class SandboxEvent(SandboxAvailability, Scene):

    event_activation: EventActivationType = 'selectable'
    repeatable: bool | int = False   # change default to one-time
    probability: float = 1.0         # certain if conditions are met

    sb_time_cost: SandboxTimeDelta = 0


# If a loc has events, it is assumed that the cursor must be at that loc, can specify additional req_loc_tags
# If a role has events, it is assumed that the actor for that role must be present, can specify additional req_loc_tags


class SandboxLocation(SandboxAvailability, HasSandboxEvents, Location):

    @property
    def sb_time(self):
        parent: Sandbox
        return self.parent.sb_time

    @AvailabilityHandler.strategy
    def _include_inferred_loc_req(self):
        return [f'self == current_loc']


SandboxSchedule = list[tuple[SandboxTimeCondition, SandboxLocation]]

class SandboxRole(SandboxAvailability, HasSandboxEvents, Role):

    sb_schedule: SandboxSchedule = None

    def get_location(self):
        ...

    # trigger and logic for update loc

    @AvailabilityHandler.strategy
    def _include_inferred_role_req(self):
        return [ f'self.loc == current_loc' ]


class SandboxNode(HasSandboxEvents, SandboxAvailability, StoryNode):
    # this is a container for a set of roles, events (scenes), and locations
    # its start block is generally a dynamic menu for selectable events from itself,
    #   its locs, and its present roles, and its connections
    # complex __on_enter__ redirect that searches for forced events

    # like edges
    connection_refs: list[UniqueLabel | Uid]

    @property
    def connections(self) -> list[SandboxNode]:

        def dereference_successor(successor_ref: UniqueLabel | Uid):
            if successor_ref:
                key_candidates = [self.successor_ref]
                if self.sandbox:
                    key_candidates.append(f"{self.sandbox.label}/{self.successor_ref}")
                for key in key_candidates:
                    try:
                        return self.graph.get_node(key)
                    except KeyError:
                        pass
                raise KeyError(f"Can't find successor called {key_candidates}")

        for connection_ref in self.connection_refs:
            return dereference_successor(connection_ref)

    @property
    def sb_time(self):
        parent: Sandbox
        return self.parent.sb_time

    @property
    def roles(self: Node) -> list[SandboxRole]:
        return self.find_children(SandboxRole)

    @property
    def locations(self: Node) -> list[SandboxLocation]:
        return self.find_children(SandboxLocation)

    @property
    def events(self: Node) -> list[SandboxEvent]:
        candidates = []
        candidates += self.find_children(SandboxEvent)
        for role in self.roles:
            # Need to include inferred role req in these
            candidates += role.find_children(SandboxEvent)
        for loc in self.locations:
            # Need to include inferred loc req in these
            candidates += loc.find_children(SandboxEvent)
        return candidates


class Sandbox(HasSandboxEvents):
    sb_time: SandboxTime = None
    sb_cursor: UniqueLabel = None

    @property
    def sb_nodes(self: Node) -> list[SandboxNode]:
        return self.find_children(SandboxNode)

    @NamespaceHandler.strategy
    def _include_current_time_and_loc(self):
        return {'sb_time': self.sb_time,
                'sb_cursor': self.sb_cursor}


#############

class SandboxGridHandler:

    @classmethod
    def incr_cursor(cls,
                    sb: SandboxGrid,
                    sb_pos_delta: SandboxPositionDelta,
                    sb_time_delta: SandboxTimeDelta):
        sb_time = sb.sb_time + sb_time_delta
        sb_pos = (sb.sb_pos[0] + sb_pos_delta[0], sb.sb_cursor[1] + sb_pos_delta[1])
        cls.set_cursor(sb, sb_time, sb_pos)

    @classmethod
    def set_cursor(cls, sb: SandboxGrid, sb_time: SandboxTime, sb_pos: SandboxPosition):
        new_sb_node = sb.get_sb_node(sb_pos)
        if not new_sb_node.available(sb_time=sb_time):
            raise StoryAccessError(f"Sandbox node {new_sb_node}@{sb_time} is not available and cannot be entered!")
        sb.sb_time = sb_time
        sb.sb_pos = sb_pos
        TraversalHandler.enter(sb)  # this will try to invoke the current block


class SandboxGrid(Sandbox):
    # GridSandbox infers connections using i,j coordinates
    sb_pos: SandboxPosition = (0, 0)
    sb_nodes: list[list[SandboxNode]] = None

    def get_sb_node(self, pos: SandboxPosition) -> SandboxNode:
        uid = self.sb_nodes[pos[0]][pos[1]]
        return self.get_child(uid)

    def get_current_sb_node(self) -> SandboxNode:
        return self.get_sb_node(self.sb_pos)

    @TraversalHandler.enter_strategy
    def _redirect_to_current_sb_node(self):
        return self.get_current_sb_node()


# class SandboxNodeType(Flag):
#     """
#     This is an example for a simple Civilization-like world-map metaphor.
#     """
#     # W always alone
#     # Only 1 of M,P (terrain)
#     # Only 1 of D,F,S (climate)
#     # No MS
#     # Only 1 of R,C,X (development)
#     M = "mountain"
#     P = "plain"
#
#     D = "desert"
#     F = "forest"
#     S = "wetlands"
#
#     W = "water"
#
#     R = "road"  # scattered population
#     C = "city"  # well-developed
#     X = "fortified"  # hardened
#
#
# SBNT = SandboxNodeType
#
# map = """\
# m m w f c w
# m w f r f w
# m p r p p w
# x r p p s w
# """