from enum import Enum

class ServiceKind(Enum):

    # Bootstrapping services
    SCOPE_DISCOVERY = "scope_discovery"      # ordered list of handler registries
    SERVICE_DISCOVERY = "service_discovery"  # ordered list of service handlers per scope

    # Factory services
    INIT = "init"            # build and link initial resources and define initial state

    # Stepper services
    GATHER = "gather"        # gather scoped services and context
    PROVISION = "provision"  # find or build and link resources on graph, check for req choice
    EFFECTS = "effect"       # mutate state
    RENDER = "render"        # generate content fragments, append to journal
