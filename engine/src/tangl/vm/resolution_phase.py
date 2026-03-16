from __future__ import annotations

from typing import Any, Callable, Type, Self, Optional, Iterable
from dataclasses import dataclass
from enum import IntEnum
import logging

from tangl.core import AggregationMode, Record

Fragment = Patch = Record

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class ResolutionPhase(IntEnum):
    """
    Phases in a single resolution step.

    Why
    ----
    Defines the ordered pipeline for one frame and the vm phase-bus
    aggregation contracts used by :mod:`tangl.vm.dispatch`.

    Key Features
    ------------
    * **Order** – ``INIT → VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE → POSTREQS``.
    * **Explicit reduction** – each phase has a concrete aggregated result
      shape enforced by ``do_*`` dispatch helpers.

    Notes
    -----
    * ``PLANNING`` in vm is side-effect-only provisioning; handlers must
      return ``None`` (non-``None`` raises ``TypeError`` in ``do_provision``).
    * ``JOURNAL`` returns ``Record | Iterable[Record] | None``.
    * ``FINALIZE`` returns ``Record | None``.
    """

    INIT = 0         # Does not run, just indicates not started
    VALIDATE = 10    # check avail new cursor Predicate, return ALL true or None
    PLANNING = 20    # resolve Dependencies and Affordances; side effects only
    PREREQS = 30     # return ANY (first) avail prereq edge to a provisioned node to break and redirect
    UPDATE = 40      # mutates graph/data in place; handlers return None
    JOURNAL = 50     # returns Record | Iterable[Record] | None
    FINALIZE = 60    # returns Record | None
    POSTREQS = 70    # return ANY (first) avail postreq edge to avail, provisioned node to break and redirect

    @classmethod
    def ordered_phases(cls) -> list[Self]:
        """Return phases in execution order."""
        return sorted([ x for x in cls.__members__.values() if x is not cls.INIT], key=lambda phase: phase.value)

    # @dataclass
    # class PhaseSpec:
    #     task: str
    #     aggregation_mode: AggregationMode
    #     result_kind: Type[Any]
    #
    #     def dispatch_func(self, *args, **kwargs):
    #         # call do_validate etc here?  Really want to use this to assemble the dispatch api
    #         ...
    #
    # def phase_spec(self) -> Optional[PhaseSpec]:
    #     if self is self.INIT:
    #         return None
    #
    #     from tangl.vm.traversal import TraversableEdge
    #     # from tangl.vm.dispatch import do_validate, do_planning, do_prereqs, do_update, do_journal, do_finalize, do_postreqs
    #     phase_specs = {
    #         self.VALIDATE: self.PhaseSpec("validate", AggregationMode.ALL_TRUE, bool),
    #         self.PLANNING: self.PhaseSpec("planning", AggregationMode.GATHER, Any),
    #         self.PREREQS: self.PhaseSpec("prereqs", AggregationMode.FIRST, Optional[TraversableEdge]),
    #         self.UPDATE: self.PhaseSpec("update", AggregationMode.GATHER, Any),
    #         self.JOURNAL: self.PhaseSpec("journal", AggregationMode.PIPE, Iterable[Fragment]),
    #         self.FINALIZE: self.PhaseSpec("finalize", AggregationMode.PIPE, Patch),
    #         self.POSTREQS: self.PhaseSpec("postreqs", AggregationMode.FIRST, Optional[TraversableEdge]),
    #     }
    #     return phase_specs[self]

