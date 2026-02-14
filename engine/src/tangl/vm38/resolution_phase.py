from __future__ import annotations

from typing import Any, Callable, Type, Self, Optional, Iterable
from dataclasses import dataclass
from enum import IntEnum
import logging

from tangl.core38 import AggregationMode, Record

Fragment = Patch = Record

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class ResolutionPhase(IntEnum):
    """
    Phases in a single resolution step.

    Why
    ----
    Defines the ordered pipeline for one frame and specifies how to **reduce**
    the list of :class:`~tangl.core.dispatch.call_receipt.CallReceipt` objects
    produced during each phase into a single outcome.

    Key Features
    ------------
    * **Order** – ``INIT → VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE → POSTREQS``.
    * **Separation of concerns** – planning/journal/finalize have distinct outputs
      (choices or receipts, fragments, patch), enabling auditing and replay.

    Notes
    -----
    * The *planning* phase typically composes to a
      :class:`~tangl.vm.planning.PlanningReceipt`.
    * The *journal* phase composes authored output into :class:`list`\\[:class:`~tangl.core.BaseFragment`] (UX).
    * The *finalize* phase serializes event‑sourced mutations into a :class:`~tangl.vm.replay.Patch`.
    """

    INIT = 0         # Does not run, just indicates not started
    VALIDATE = 10    # check avail new cursor Predicate, return ALL true or None
    PLANNING = 20    # resolve Dependencies and Affordances; updates graph/data on frontier in place and GATHERS receipts
    PREREQS = 30     # return ANY (first) avail prereq edge to a provisioned node to break and redirect
    UPDATE = 40      # mutates graph/data in place and GATHERS receipts
    JOURNAL = 50     # return PIPES receipts to compose a list of FRAGMENTS
    FINALIZE = 60    # cleanup, commit events, consume resources, etc.; updates graph/data in place and PIPE receipts to compose a Patch
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
    #     from tangl.vm38.traversal import TraversableEdge
    #     # from tangl.vm38.dispatch import do_validate, do_planning, do_prereqs, do_update, do_journal, do_finalize, do_postreqs
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


