"""tangl.story.reference_domain

Reference domain publishing lightweight story primitives used by integration
and CLI samples. The goal is determinism and clarity rather than dramatic
scope.

Exports
-------
- :class:`~tangl.story.reference_domain.concept.SimpleConcept`
"""

from __future__ import annotations

from .block import SimpleBlock
from .concept import SimpleConcept

__all__ = [
    "SimpleBlock",
    "SimpleConcept",
]
