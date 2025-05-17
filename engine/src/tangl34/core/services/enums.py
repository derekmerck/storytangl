from enum import Enum

class Service(str, Enum):

    # Bootstrapping services
    SCOPE_DISCOVERY = "scope_discovery"      # ordered list of handler registries
    SERVICE_DISCOVERY = "service_discovery"  # ordered list of service handlers per scope

    # Factory services
    INIT = "init"            # on_init_graph, link resources and mutate state

    # Stepper services
    GATHER = "gather"        # on_gather, gather scoped services and context
    PROVISION = "resolve"    # on_find, on_build, link resources on graph, check for choice pre-req
    EFFECTS = "effect"       # on_update, effects mutate state
    RENDER = "render"        # on_render, generate content fragments, append to journal
    FINALIZE = "exit"        # on_finalize -> post-effects mutate state, check for choice post-req
