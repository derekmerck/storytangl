from __future__ import annotations
from typing import Any, Callable, Type, Self
from enum import IntEnum, Enum
import logging

from tangl.core import Edge, CallReceipt, BaseFragment
from .replay import Patch

logger = logging.getLogger(__name__)

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
    * **Aggregation policy** – each phase maps to a reducer and an expected result type.
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
    DISCOVER = 10    # build context, discover capabilities in scope
    VALIDATE = 20    # check avail new cursor Predicate, return ALL true or None
    PLANNING = 30    # resolve Dependencies and Affordances; updates graph/data on frontier in place and GATHERS receipts
    PREREQS = 40     # return ANY (first) avail prereq edge to a provisioned node to break and redirect
    UPDATE = 50      # mutates graph/data in place and GATHERS receipts
    JOURNAL = 60     # return PIPES receipts to compose a list of FRAGMENTS
    FINALIZE = 70    # cleanup, commit events, consume resources, etc.; updates graph/data in place and PIPE receipts to compose a Patch
    POSTREQS = 80    # return ANY (first) avail postreq edge to avail, provisioned node to break and redirect

    @classmethod
    def ordered_phases(cls) -> list[Self]:
        """Return phases in execution order."""
        return sorted(cls.__members__.values(), key=lambda phase: phase.value)

    def properties(self) -> tuple[Callable, Type]:
        """Aggregation func and expected final result type by phase"""
        _data = {
            self.INIT: None,
            self.VALIDATE: (CallReceipt.all_truthy,   bool),     # confirm all true
            self.PLANNING: (CallReceipt.last_result,  CallReceipt),  # actually a PlanningReceipt
            self.PREREQS:  (CallReceipt.first_result, Edge),     # check for any available jmp/jr
            self.UPDATE:   (CallReceipt.gather_results, Any),
            self.JOURNAL:  (CallReceipt.last_result,  list[BaseFragment]), # pipe and compose a list of Fragments
            self.FINALIZE: (CallReceipt.last_result,  Patch),    # pipe and compose a Patch (if event sourced)
            self.POSTREQS: (CallReceipt.first_result, Edge)      # check for any available jmp/jr
        }
        return _data[self]

