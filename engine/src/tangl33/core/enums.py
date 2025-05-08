from enum import IntEnum

class Phase(IntEnum):
    """There are 5 phases in handling a step"""
    GATHER_CONTEXT = 10   # provider should return a context layer
    CHECK_REDIRECTS = 20  # provider should return an optional edge
    PROVISION_NEXT = 30   # provider should work in-place on node/graph?
    APPLY_EFFECTS = 40    # provider should work in-place on node/graph
    RENDER = 50           # provider should return a list of content fragments?
    FINALIZE = 60         # provider should work in-place on node/graph
    CHECK_CONTINUES = 70  # provider should return an optional edge

class Tier(IntEnum):
    """
    There are 7 scope tiers in context evaluation.
    Adding a provider for a phase at the 'priority' tier will force first,
    adding at the 'default' tier will run it last or possibly not at all if
    a result has already been returned
    """
    PRIORITY = FIRST = 10   # do _before_ the normal phase actions
    NODE = 20
    ANCESTORS = 30
    GRAPH = 40
    DOMAIN = 50
    GLOBAL = 60
    DEFAULT = LAST = 70     # do _after_ the normal phase actions
