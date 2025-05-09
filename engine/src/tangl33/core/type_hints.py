"""
tangl.core.type_hints
=====================

Type definitions for StoryTangl's domain-specific concepts.

This module provides centralized type definitions that enable:
- Static type checking through mypy/pyright
- Self-documenting interfaces
- Consistency across the codebase

Key type hints include:
- ProvisionKey: Identifier for resource providers
- Context: Mapping for variable scopes
- Predicate: Functions for conditional evaluation

These type definitions bridge the gap between StoryTangl's conceptual
model and Python's type system, making the codebase more maintainable
and self-documenting.
"""

from typing import Mapping, Any, Callable

ProvisionKey = str

# ------------------------------------------------------------
# Predicates & helper aliases
# ------------------------------------------------------------
Context = Mapping[str, Any]
Predicate = Callable[[Context], bool]          # return True to run
