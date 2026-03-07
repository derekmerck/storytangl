"""
.. currentmodule:: tangl.story.episode

Story cursor vocabulary built on top of the vm traversal contracts.

Conceptual layers
-----------------

1. :class:`Block` stores authored narrative content, role/setting bindings, and
   available outgoing actions.
2. :class:`Scene` groups blocks into containers with source and sink contracts.
3. :class:`Action` links blocks through choices, redirects, and continuations.

Design intent
-------------
This package defines story-facing node semantics while delegating generic graph
movement rules to :mod:`tangl.vm`.
"""

from .action import Action
from .block import Block
from .scene import Scene

__all__ = ["Action", "Block", "Scene"]
