"""
.. currentmodule:: tangl.vm.replay

Replay contracts, records, and engines for deterministic runtime history.

Conceptual layers
-----------------

1. :class:`Event` and :class:`Patch` capture runtime deltas.
2. :class:`StepRecord`, :class:`CheckpointRecord`, and
   :class:`RollbackRecord` preserve execution history.
3. :class:`ReplayEngine` and :class:`DiffReplayEngine` apply or reconstruct
   those deltas.

Design intent
-------------
Replay stays separate from live traversal so history, rollback, and diffing can
evolve without changing the story or provisioning surfaces.
"""

from .contracts import ReplayDelta, ReplayEngine
from .engine import DEFAULT_ALGORITHM_ID, DiffReplayEngine, get_replay_engine
from .patch import Event, OpEnum, Patch
from .records import (
    CausalityTransitionRecord,
    CheckpointRecord,
    RollbackRecord,
    StepRecord,
)

__all__ = [
    "CheckpointRecord",
    "CausalityTransitionRecord",
    "DEFAULT_ALGORITHM_ID",
    "DiffReplayEngine",
    "Event",
    "OpEnum",
    "Patch",
    "ReplayDelta",
    "ReplayEngine",
    "RollbackRecord",
    "StepRecord",
    "get_replay_engine",
]
