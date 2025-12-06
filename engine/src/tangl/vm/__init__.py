"""
.. currentmodule:: tangl.vm

Virtual Machine for executing resolution steps over self-realizing narrative graphs.
These classes define the *processes* (verbs) that operate on the foundational data
structures of :mod:`tangl.core`.

Conceptual layers
-----------------

1. :ref:`Graph Resolution<vm-resolver>`

   - :class:`Frame` executes a deterministic sequence of phases from a cursor (the program counter).
   - :class:`ResolutionPhase` enumerates and aggregates per-phase handler pipelines.
   - :class:`Context` provides the working graph, cursor, scope, and seeded RNG for one step.
   - :class:`Ledger` holds the live :class:`~tangl.core.Graph`, current cursor,
     and the append-only stream of patches, snapshots, and fragments.

   Each cursor advance provokes a cascade of phase handlers that validate, extend,
   and navigate the resolution frontier. The ledger can rehydrate graphs from the
   event stream and provide Journal fragments for discourse/presentation.

2. :ref:`Planning<vm-planning>`

   - :class:`Requirement` expresses needed providers and their provisioning policy.
   - :class:`Provisioner` resolves or creates providers according to policy.
   - :class:`Offer` (alias for :class:`ProvisionOffer`) represents a proposed way to satisfy a requirement.
   - :class:`Dependency` and :class:`Affordance` describe open edges at the frontier.

3. :ref:`Replay<vm-replay>`

   - :class:`Event` and :class:`EventType` capture CRUD operations as immutable records.
   - :class:`Patch` and :class:`~tangl.core.Snapshot` provide reliable state reconstruction.
   - :mod:`~tangl.vm.replay.watched_proxy` instruments entities/registries (event-sourced mutation capture).
   - Canonicalization produces stable, minimal patch deltas for deterministic replay.

Design intent
-------------
`tangl.vm` orchestrates how story graphs evolve during resolution. It defines the
execution semantics—phases, handlers, planning, and event replay—without imposing
any narrative or domain-specific content. VM code depends only on :mod:`tangl.core`
(and lightweight utils).

Notes
-----
*Design note:* `vm` uses dataclasses for ephemeral execution (`Frame`, `Context`) and Pydantic models for persisted artifacts (`Ledger`, `Event`, `Patch`, Receipts).
"""

# Event sourced state manager
from .replay import Event, EventType, EventWatcher, Patch

# Resolution step
from .resolution_phase import ResolutionPhase
from .context import Context
from .frame import Frame, ChoiceEdge, StackFrame
from .stack_snapshot import StackSnapshot
from .ledger import Ledger
from .traversal import (
    TraversableSubgraph,
    get_visit_count,
    is_first_visit,
    steps_since_last_visit,
    is_self_loop,
    in_subroutine,
    get_caller_frame,
    get_call_depth,
    get_root_caller,
)

# Dispatch
from .dispatch import vm_dispatch

# Provisioning
from .provision import (
    Requirement,
    Provisioner,
    GraphProvisioner,
    TemplateProvisioner,
    UpdatingProvisioner,
    CloningProvisioner,
    CompanionProvisioner,
    Dependency,
    Affordance,
    ProvisioningPolicy,
    ProvisionOffer,
    DependencyOffer,
    AffordanceOffer,
    ProvisionCost,
    BuildReceipt,
    PlanningReceipt,
)
from .debug import PlanningDebugger

Offer = ProvisionOffer

__all__ = [
    # events/replay
    "Event",
    "EventType",
    "Patch",
    # resolution
    "Frame",
    "ChoiceEdge",
    "StackFrame",
    "StackSnapshot",
    "ResolutionPhase",
    "Ledger",
    "Context",
    "TraversableSubgraph",
    "get_visit_count",
    "is_first_visit",
    "steps_since_last_visit",
    "is_self_loop",
    "in_subroutine",
    "get_caller_frame",
    "get_call_depth",
    "get_root_caller",
    # dispatch
    "vm_dispatch",
    # planning
    "Requirement",
    "Provisioner",
    "GraphProvisioner",
    "TemplateProvisioner",
    "UpdatingProvisioner",
    "CloningProvisioner",
    "CompanionProvisioner",
    "Dependency",
    "Affordance",
    "ProvisioningPolicy",
    "Offer",
    "ProvisionOffer",
    "DependencyOffer",
    "AffordanceOffer",
    "ProvisionCost",
    "BuildReceipt",
    "PlanningReceipt",
    "PlanningDebugger",
]
