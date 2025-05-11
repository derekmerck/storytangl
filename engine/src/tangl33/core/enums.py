"""
tangl.core.enums
================

Core execution model enums defining the traversal protocol.

StoryTangl organizes its execution model through two primary dimensions:

- **Phase**: Determines what type of operation is being performed
  (context gathering, redirection, content generation, etc.)

- **Tier**: Defines the scope in which operations execute
  (node-local, ancestor chain, graph-wide, domain-wide, etc.)

These enums establish a consistent, deterministic ordering system
that makes story traversal predictable while maintaining flexibility
in how capabilities are inserted and executed.

The traversal protocol ensures that the story space "collapses"
in a principled way from outer tiers (global) to inner ones (node),
and from earlier phases to later ones.

This module also provides utility methods for iterating through
tiers in different directions (inwards vs. outwards).
"""

from enum import IntEnum, Enum, auto

from tangl33.utils.smart_missing import SmartMissing

class Service(SmartMissing, Enum):
    PROVIDER = auto()  # creates a node/tree that satisfies a requirement, provides a new node-like to link
    TEMPLATE = auto()  # provides templates to meet requirements, sub-service for provider
    CONTEXT = auto()   # provides a layered context map
    GATE = auto()
    EFFECT = auto()    # mutates graph
    RENDER = auto()    # provides a list of fragments for the journal
    CHOICE = auto()    # provides structural edges to further content, user trigger:before or trigger:after to auto-follow

# todo: Don't need "phase" anymore?  Use service instead?
class Phase(SmartMissing, IntEnum):
    """There are multiple phases in handling a step"""
    GATHER = 10          # context services only
    RESOLVE = 20          # 5 services can register here: builder, gate, before choice, effect
    RENDER = 30           # render services only
    FINALIZE = 40         # 2 services can register here: effect, after choice

class Tier(SmartMissing, IntEnum):
    """
    There are multiple scope tiers in context evaluation.
    Adding a provider for a phase at the 'priority' tier will force first,
    adding at the 'default' tier will run it last or possibly not at all, if
    a result can be returned earlier.
    """
    PRIORITY = FIRST = 10   # do _before_ the normal scope actions
    NODE = 20               # graph.node
    ANCESTORS = 30          # active subgraph
    GRAPH = 40              # graph.graph
    DOMAIN = 50             # graph.domain
    USER = 60
    GLOBAL = 70             # graph.global_scope
    DEFAULT = LAST = 80     # do _after_ the normal scope actions

    @classmethod
    def range_outwards(cls, start: "Tier | int | None" = None):
        """
        Return tiers from *inner* to *outer* (NODE → … → GLOBAL).
        If *start* is given, begin at that tier (inclusive).
        """
        tiers = sorted(iter(cls), key=int)                 # ascending: PRIORITY(10)…DEFAULT(80)
        if start is None:
            return tiers
        start = cls(start) if not isinstance(start, cls) else start
        try:
            return tiers[tiers.index(start):]
        except ValueError:                                 # should not happen
            return tiers

    @classmethod
    def range_inwards(cls, start: "Tier | int | None" = None):
        """
        Return tiers from *outer* to *inner* (GLOBAL → … → NODE).
        If *start* is given, begin at that tier (inclusive).
        """
        tiers = sorted(iter(cls), key=int, reverse=True)
        if start is None:
            return tiers
        start = cls(start) if not isinstance(start, cls) else start
        try:
            return tiers[tiers.index(start):]
        except ValueError:
            return tiers
