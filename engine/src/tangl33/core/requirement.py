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


# built-in “direct” strategy
class DirectStrategy:
    def create(self, req: "Requirement", ctx):
        raise ProvisionError(f"No provider for {req.key!r}")


@dataclass(slots=True)
class Requirement:
    """
    A request for *something* (actor, item, shop, …).

    • **key**       – canonical string the provider advertises in `ProvisionCap.provides`
    • **strategy**  – object implementing the Strategy protocol
    • **params**    – opaque dict passed to predicates / factories
    • **tier**      – where the *requester* sits (defaults to its node)
    """
    key: str
    strategy: Strategy = DirectStrategy()
    params: Dict[str, Any] = field(default_factory=dict)
    tier: Tier = Tier.NODE

    # hash / eq let us memoise during recursive resolution
    def __hash__(self): return hash((self.key, frozenset(self.params.items()), self.tier))
    def __eq__(self, other): return (
        isinstance(other, Requirement)
        and self.key == other.key
        and self.params == other.params
        and self.tier == other.tier
    )
