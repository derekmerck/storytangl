"""
VM behavior patterns.

Pre-built handlers for common traversal patterns such as call/return.
"""
from __future__ import annotations

from .subroutine import auto_return_from_subgraph, conditional_return

__all__ = [
    "auto_return_from_subgraph",
    "conditional_return",
]
