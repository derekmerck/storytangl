"""
.. currentmodule:: tangl.vm.runtime

Execution-state models for phase-driven traversal.

Conceptual layers
-----------------

1. :class:`Frame` executes one resolution loop over a current cursor.
2. :class:`Ledger` persists cursor history, replay records, and stack state
   across frames.
3. :class:`CausalityMode` describes how aggressively the runtime may accept
   topology-changing operations.

Design intent
-------------
This package owns runtime state progression rather than provisioning policy or
story-layer semantics.
"""

from .causality import CausalityMode
from .frame import Frame
from .ledger import Ledger

__all__ = ["CausalityMode", "Frame", "Ledger"]
