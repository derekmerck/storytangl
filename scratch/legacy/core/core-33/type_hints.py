"""
tangl.core.type_hints
=====================

Type definitions for StoryTangl's domain-specific concepts.

This module provides centralized type definitions that enable:
- Static type checking through mypy/pyright
- Self-documenting interfaces
- Consistency across the codebase
"""

from typing import Mapping, Any, Callable, Protocol

ProvisionKey = str

# ------------------------------------------------------------
# Predicates & helper aliases
# ------------------------------------------------------------
StringMap = Mapping[str, Any]
Predicate = Callable[[StringMap], bool]          # return True to run

class ScopeP(Protocol):
    # service handlers
    def handler_layer(self): ...   # Returns a callable registry?
    # provisioning resources
    def template_layer(self): ...  # Returns?
    # context data, layer may be a map or a list[map] to be folded into the TierView
    def local_layer(self, service) -> StringMap | list[StringMap]: ...
