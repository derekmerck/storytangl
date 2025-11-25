"""
Dialogue and other micro-block discourse helpers.

This subpackage hosts ephemeral parsing artifacts that shape story content
without persisting in the graph. See :mod:`tangl.story.discourse.mu_block`
for the base :class:`~tangl.story.discourse.mu_block.MuBlock` abstraction and
:mod:`tangl.story.discourse.dialog` for dialog-specific parsing.
"""
from __future__ import annotations

from .mu_block import MuBlock, MuBlockHandler
from .dialog import DialogHandler, DialogMuBlock

__all__ = [
    "MuBlock",
    "MuBlockHandler",
    "DialogHandler",
    "DialogMuBlock",
]
