# Provides:
# - stable names for phase bus stages
from .resolution_phase import ResolutionPhase

# Provides:
# - requirements/providers
# - resolution
# - frontier planning
from .provision import (
    Affordance,
    Dependency,
    FallbackProvisioner,
    FindProvisioner,
    HasRequirement,
    InlineTemplateProvisioner,
    Provisioner,
    ProvisionOffer,
    ProvisionPolicy,
    Requirement,
    Resolver,
    TemplateProvisioner,
)

# Provides:
# - cursor traversal rules
from .traversable import (
    TraversableEdge,
    TraversableNode,
    AnonymousEdge,
    assert_traversal_contracts,
    validate_traversal_contracts,
)
from .traversal import (
    count_turns,
    get_call_depth,
    get_visit_count,
    in_subroutine,
    is_first_visit,
    is_self_loop,
    steps_since_last_visit,
)

# Provides:
# - phase bus
# - serializable graph with state and trace artifacts
# - jump and return stack
from .runtime import Frame, Ledger

# Provides:
# - journal fragment records
from .fragments import Fragment

# Provides:
# - phase bus hooks
from .dispatch import (
    on_finalize,
    on_gather_ns,
    on_journal,
    on_postreqs,
    on_prereqs,
    on_provision,
    on_resolve,
    on_update,
    on_validate,
)


__all__ = [
    "Affordance",
    "AnonymousEdge",
    "Dependency",
    "FallbackProvisioner",
    "FindProvisioner",
    "Frame",
    "Fragment",
    "HasRequirement",
    "InlineTemplateProvisioner",
    "Ledger",
    "Provisioner",
    "ProvisionOffer",
    "ProvisionPolicy",
    "Requirement",
    "ResolutionPhase",
    "Resolver",
    "TemplateProvisioner",
    "TraversableEdge",
    "TraversableNode",
    "count_turns",
    "get_call_depth",
    "get_visit_count",
    "in_subroutine",
    "is_first_visit",
    "is_self_loop",
    "assert_traversal_contracts",
    "on_finalize",
    "on_gather_ns",
    "on_journal",
    "on_postreqs",
    "on_prereqs",
    "on_provision",
    "on_resolve",
    "on_update",
    "on_validate",
    "steps_since_last_visit",
    "validate_traversal_contracts",
]
