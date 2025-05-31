"""
tangl.core.enums
================

Core execution model enums defining the traversal protocol.

StoryTangl organizes its execution model through three primary dimensions:

- **CoreService**: Determines what type of operation is being performed
  (context gathering, node creation, content generation, etc.)

- **CoreScope**: Defines the scope in which operations execute
  (node-local, ancestor chain, graph-wide, domain-wide, etc.)

These enums establish a consistent, deterministic ordering system
that makes story traversal predictable while maintaining flexibility
in how capabilities are inserted and executed.

The traversal protocol ensures that the story space "collapses"
in a principled way from inner tiers (node-local) to outer ones
(domain-wide), and from earlier phases to later ones.

This module also provides utility methods for iterating through
tiers in different directions (inwards vs. outwards).
"""

from enum import IntEnum, Enum, auto

from tangl33.utils.smart_missing import SmartMissing

class CoreService(SmartMissing, Enum):
    PROVIDER = auto()  # creates a node/tree that satisfies a requirement, provides a new node-like to link
    TEMPLATE = auto()  # provides templates to meet requirements, sub-service for provider
    CONTEXT = auto()   # provides a namespace mapping, sub-service for all other services
    GATE = auto()      # demotes providers to latent if availability predicates are not met
    EFFECT = auto()    # mutates graph, triggered BEFORE and AFTER content handling
    RENDER = auto()    # provides a list of content fragments for the journal
    CHOICE = auto()    # provides structural edges to further content, may auto-follow BEFORE or AFTER effects and content handling

class CoreScope(SmartMissing, IntEnum):
    """
    There are multiple scope tiers in context evaluation.

    Adding a provider for a phase at the 'priority' CoreScope will force first,
    adding at the 'default' CoreScope will run it last or possibly not at all, if
    a result is provided earlier.
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
    def range_outwards(cls, start: "CoreScope | int | None" = None):
        """
        Return tiers from *inner* to *outer* (NODE → … → GLOBAL).
        If *start* is given, begin at that CoreScope (inclusive).
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
    def range_inwards(cls, start: "CoreScope | int | None" = None):
        """
        Return tiers from *outer* to *inner* (GLOBAL → … → NODE).
        If *start* is given, begin at that CoreScope (inclusive).
        """
        tiers = sorted(iter(cls), key=int, reverse=True)
        if start is None:
            return tiers
        start = cls(start) if not isinstance(start, cls) else start
        try:
            return tiers[tiers.index(start):]
        except ValueError:
            return tiers
