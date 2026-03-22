"""
.. currentmodule:: tangl.vm

Virtual machine mechanisms for phase-driven traversal, provisioning, and replay.

Conceptual layers
-----------------

1. Resolution runtime

   - :class:`Frame` executes one choice resolution loop.
   - :class:`Ledger` persists cursor, stack, and replay artifacts across choices.
   - :class:`ResolutionPhase` defines causal phase ordering.

2. Traversal contracts

   - :class:`TraversableNode` / :class:`TraversableEdge` define cursor movement.
   - :class:`TraversableGraph` carries traversal entry metadata for factory-built graphs.
   - :class:`TraversableGraphFactory` materializes traversal-ready graphs from templates.
   - :mod:`tangl.vm.traversal` provides pure history/call-stack queries.

3. Provisioning

   - :class:`Requirement`, :class:`Dependency`, :class:`Affordance`, and
     :class:`Fanout` define frontier constraints.
   - :class:`Resolver` and provisioners satisfy constraints from
     entity/template scopes.

4. Replay artifacts

   - :class:`Event`, :class:`Patch`, :class:`StepRecord`,
     :class:`CheckpointRecord` provide deterministic replay and rollback
     primitives.

Design intent
-------------
``tangl.vm`` defines deterministic execution mechanics and contracts while remaining
policy-agnostic about story/domain semantics, which belong in higher layers.
"""

# Provides:
# - stable names for phase bus stages
from .resolution_phase import ResolutionPhase

# Provides:
# - requirements/providers
# - resolution
# - frontier planning
from .provision import (
    Affordance,
    Blocker,
    Dependency,
    Fanout,
    StubProvisioner,
    FindProvisioner,
    HasRequirement,
    InlineTemplateProvisioner,
    Provisioner,
    ProvisionOffer,
    ProvisionPolicy,
    Requirement,
    Resolver,
    TemplateProvisioner,
    TokenProvisioner,
    UpdateCloneProvisioner,
    ViabilityResult,
    CloneProvisioner,
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
from .factory import TraversableGraph, TraversableGraphFactory
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
from tangl.core import BaseFragment as Fragment
from .replay import Event, Patch

# Provides:
# - phase bus hooks
from .dispatch import (
    do_compose_journal,
    on_compose_journal,
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
from .ctx import VmPhaseCtx
from . import system_handlers  # noqa: F401  # register default vm hooks
from tangl.core import CallReceipt as BuildReceipt, Record as PlanningReceipt


__all__ = [
    "Affordance",
    "AnonymousEdge",
    "Blocker",
    "Dependency",
    "Fanout",
    "StubProvisioner",
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
    "TokenProvisioner",
    "UpdateCloneProvisioner",
    "ViabilityResult",
    "CloneProvisioner",
    "TraversableEdge",
    "TraversableGraph",
    "TraversableGraphFactory",
    "TraversableNode",
    "Patch",
    "Event",
    "BuildReceipt",
    "PlanningReceipt",
    "count_turns",
    "get_call_depth",
    "get_visit_count",
    "in_subroutine",
    "is_first_visit",
    "is_self_loop",
    "assert_traversal_contracts",
    "do_compose_journal",
    "on_finalize",
    "on_compose_journal",
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
    "VmPhaseCtx",
]
