"""
.. currentmodule:: tangl.vm

Virtual Machine for executing resolution steps over self‑realizing narrative graphs.
These classes define the *processes* (verbs) that operate on the foundational data
structures of :mod:`tangl.core`.

Conceptual layers
-----------------

1. :ref:`Graph Resolution<vm-resolver>`

   - :class:`Frame` executes a deterministic sequence of phases over a cursor.
   - :class:`ResolutionPhase` enumerates and aggregates handler pipelines.
   - :class:`Context` provides the working graph, cursor, and scope for one step.
   - :class:`Ledger` holds the live :class:`~tangl.core.Graph`, current cursor,
     and the append‑only stream of patches, snapshots, and fragments.

2. :ref:`Planning<vm-planning>`

   - :class:`Requirement` expresses needed providers and their provisioning policy.
   - :class:`Provisioner` resolves or creates providers according to policy.
   - :class:`Offer` represents a proposed way to satisfy a requirement.
   - :class:`Dependency` and :class:`Affordance` describe open edges at the resolution frontier.

3. :ref:`Replay<vm-replay>`

   - :class:`Event` and :class:`EventType` capture CRUD operations as immutable records.
   - :class:`Patch` and :class:`~tangl.core.Snapshot` provide reliable state reconstruction.
   - :mod:`~tangl.vm.replay.watched_proxy` instruments entities and registries for event capture.

Design intent
-------------
`tangl.vm` orchestrates how story graphs evolve during resolution. It defines the
execution semantics—phases, handlers, planning, and event replay—without imposing
any narrative or domain‑specific content.
"""

# Event sourced state manager
from .replay import Event, EventType, EventWatcher, Patch

# Provisioning
from .planning import Requirement, Provisioner, Dependency, Affordance, ProvisioningPolicy, Offer

# Resolution step
from .context import Context
from .frame import Frame, ChoiceEdge, ResolutionPhase
from .ledger import Ledger

# Simple phase-bus handlers
import tangl.vm.simple_handlers

__all__ = [
    # events/replay
    "Event", "EventType", "Patch",
    # planning
    "Requirement", "Provisioner", "Dependency", "Affordance", "ProvisioningPolicy", "Offer",
    # resolution
    "Frame", "ChoiceEdge", "ResolutionPhase", "Ledger", "Context",
    ]
