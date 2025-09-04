from enum import IntEnum, auto

# Incremental resolution happens in phases.  Any scope that the node can see
# (i.e., mro, ancestor, graph, domain, user, global) hook any phase and inject their
# own logic.

# Content authors are encouraged to use custom classes where relevant with method hooks
# or confine their hooks to a private domain that nodes from their story can subscribe to.

class Phase(IntEnum):
    PREDICATE   = 10   # allowed to enter
    PROVISION   = 20   # advance resolution frontier, resolve next step dependencies, affordances
    # PREREQS     = 30   # check resolved choice predicates, redirect with jump/jr if required
    EFFECTS     = 40   # mutate state before
    # RENDER      = 50   # generate trace fragments
    # COMPOSE     = 60   # assemble journal entry from candidate trace fragments, create groups and ladders
    # BOOKKEEPING = 70   # mutate state after (e.g., consume resources that were needed for rendering)
    # POSTREQS    = 80   # check resolved choice predicates, continue automatically with jump/jr if required

    # Otherwise, the logic confirms at least one choice exists, then blocks for a selection
