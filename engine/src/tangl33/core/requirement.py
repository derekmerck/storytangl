"""
tangl.core.requirement
=====================

Declarative dependency specifications with resolution strategies.

Requirements are first-class declarations of what resources a node
needs to function properly. Key features include:

- String-based keys for provider matching
- Strategy pattern for flexible resolution approaches
- Parameter passing for contextual creation/selection
- Tiered resolution for scope control
- Built-in memoization support through hashing

Requirements provide the "pull" side of StoryTangl's architecture,
where story elements actively request the providers they need,
triggering just-in-time creation of narrative elements.

This enables dynamic, contextual story unfolding where characters,
locations, and objects appear only when narratively appropriate,
embodying the "quantum narrative" metaphor.

See Also
--------
resolver: System for matching requirements to providers
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Dict, Protocol, runtime_checkable, TYPE_CHECKING

from .type_hints import StringMap, ProvisionKey
from .enums import Tier
from .exceptions import ProvisionError

if TYPE_CHECKING:
    from .provision import ProviderCap


# ------------------------------------------------------------
# Strategy interface  (pluggable algorithms)
# ------------------------------------------------------------
@runtime_checkable
class Strategy(Protocol):
    def create(self, req: Requirement, ctx: StringMap):
        """Instantiate a new ProvisionCap when no existing provider matches."""

    def select(self, prov, req: Requirement, ctx: StringMap) -> bool:
        """Return True if *prov* satisfies *req* in the current context."""


# built-in “direct” strategy
class DirectStrategy:
    def create(self, req: Requirement, ctx: StringMap):
        raise ProvisionError(f"No provider for {req.key!r}")

    # A direct match accepts the first provider whose advertised key matches
    # and whose params (if any) are a superset of the requirement params.
    def select(self, prov: 'ProviderCap', req: Requirement, ctx):
        if req.key not in getattr(prov, "provides", ()):
            return False
        if req.criteria:
            if not prov.matches(**req.criteria):
                return False
        return True


@dataclass(slots=True)
class Requirement:
    """
    A request for *something* (actor, item, shop, …).

    • **key**       – canonical string the provider advertises in `ProvisionCap.provides`
    • **strategy**  – object implementing the Strategy protocol
    • **criteria**  – selection criteria for matching a provider
    • **params**    – opaque dict passed to predicates / factories
    • **tier**      – where the *requester* sits (defaults to its node)
    """
    key: ProvisionKey
    strategy: Strategy = DirectStrategy()
    params: StringMap = field(default_factory=dict)
    criteria: StringMap = field(default_factory=dict)
    tier: Tier = Tier.NODE  # Scope to evaluate within

    # hash / eq let us memoise during recursive resolution
    def __hash__(self): return hash((self.key, frozenset(self.params.items()), self.tier))
    def __eq__(self, other): return (
        isinstance(other, Requirement)
        and self.key == other.key
        and self.params == other.params
        and self.tier == other.tier
    )
