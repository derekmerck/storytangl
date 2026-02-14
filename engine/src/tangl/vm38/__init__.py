# Provides:
# - stable names for phase bus stages
from .resolution_phase import ResolutionPhase

# Requires:
# - core.selector, edges, materialize() pattern
# Provides:
# - requirements/providers
# - resolution
# - frontier planning
from .provision import (Requirement, HasRequirement, Dependency, Affordance,
                        ProvisionPolicy, ProvisionOffer, Provisioner,
                        TemplateProvisioner, FallbackProvisioner, FindProvisioner, TokenProvisioner,
                        Resolver)

# Requires:
# - core.graph
# Provides:
# - cursor traversal rules
from .traversable import TraversableEdge, TraversableNode, AnonymousEdge

# Requires:
# - core.entity, graph
# Provides:
# - stable replay
# from .replay import ObservedEntity, ObservedGraph, Observer, Event, Patch

# Requires:
# - core.graph
# - vm.resolution_phase
# - vm.planning
# - vm.traversal
# - vm.replay
# Provides:
# - phase bus
# - serializable graph with state and trace artifacts
# - jump and return stack
from .runtime import Frame, Ledger

# Requires:
# - vm.resolution_phase
# Provides
# - phase bus hooks
from .dispatch import on_validate, on_provision, on_resolve, on_prereqs, on_update, on_journal, on_finalize, on_postreqs
