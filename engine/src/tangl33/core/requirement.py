from dataclasses import dataclass, field
from typing import Any, Mapping, Dict, Protocol, runtime_checkable

from .enums import Tier
from .exceptions import ProvisionError


# ------------------------------------------------------------
# Strategy interface  (pluggable algorithms)
# ------------------------------------------------------------
@runtime_checkable
class Strategy(Protocol):
    def create(self, req: "Requirement", ctx: Mapping[str, Any]):
        """Instantiate a new ProvisionCap when no existing provider matches."""

    def select(self, prov, req: "Requirement", ctx: Mapping[str, Any]) -> bool:
        """Return True if *prov* satisfies *req* in the current context."""


# built-in “direct” strategy
class DirectStrategy:
    def create(self, req: "Requirement", ctx):
        raise ProvisionError(f"No provider for {req.key!r}")

    # A direct match accepts the first provider whose advertised key matches
    # and whose params (if any) are a superset of the requirement params.
    def select(self, prov, req: "Requirement", ctx):
        if req.key not in getattr(prov, "provides", ()):
            return False
        if req.criteria:
            if not prov.matches(req.criteria):
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
    key: str
    strategy: Strategy = DirectStrategy()
    params: Dict[str, Any] = field(default_factory=dict)
    criteria: Dict[str, Any] = field(default_factory=dict)
    tier: Tier = Tier.NODE

    # hash / eq let us memoise during recursive resolution
    def __hash__(self): return hash((self.key, frozenset(self.params.items()), self.tier))
    def __eq__(self, other): return (
        isinstance(other, Requirement)
        and self.key == other.key
        and self.params == other.params
        and self.tier == other.tier
    )
