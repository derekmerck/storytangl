from enum import Enum

class ServiceKind(Enum):

    # Factory services
    INIT = "init"            # build and link initial resources and define initial state

    # Stepper services
    CONTEXT = "context"      # gather scoped context
    PROVISION = "provision"  # find or build and link resources on graph, check for req'd choice before or after
    EFFECT = "effect"        # mutate state, before or after
    RENDER = "render"        # generate content fragments, append to journal
