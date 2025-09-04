# tangl/vm/provisioning/ticket.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Optional, Callable, Literal
from uuid import UUID
from tangl.vm36.execution.tick import StepContext

# ---------- Requirement ----------

@dataclass(frozen=True)
class ProvisionRequirement:
    """
    Declarative requirement for provisioning (or attachment affordances).
    """
    kind: str                    # "role", "entity", "media", ...
    name: str                    # e.g. "villain", "inline-image"
    constraints: Mapping[str, object] | None = None
    policy: Mapping[str, object] | None = None
    meta: Mapping[str, object] | None = None

    def norm_policy(self) -> dict[str, object]:
        p = dict(self.policy or {})
        p.setdefault("optional", False)
        p.setdefault("create_if_missing", False)
        p.setdefault("prune_if_unsatisfied", True)
        return p

    def fingerprint(self) -> tuple:
        # Stable key for diagnostics/tie-breaking (constraints/meta kept shallow)
        return (self.kind, self.name, tuple(sorted((self.constraints or {}).items())))

# ---------- Provision Offer (quote) ----------

@dataclass(frozen=True)
class ProvisionOffer:
    """
    A quoted plan to satisfy a requirement.
    Accepting it must be idempotent and return the bound resource UID.
    """
    resolver_id: str             # stable id of the resolver (e.g., "role.finder.default")
    kind: str                    # requirement kind this satisfies
    cost: int                    # lower = preferred; deterministic
    label: str                   # human/readable description
    # If this is a bind-to-existing quote, fill existing_uid (accept must still be called)
    existing_uid: Optional[UUID] = None
    # Perform realization/bind; must return the resource UID that fulfills the requirement
    accept: Callable[[StepContext, UUID], UUID] | None = None
    # The requirement this quote satisfies (None if it's a pure affordance quote)
    req: Optional[ProvisionRequirement] = None
    # Guard for availability; same shape as narrative Offer guard
    guard: Callable[[object, object, StepContext, UUID], bool] = field(
        default=lambda g, facts, ctx, owner_uid: True
    )

    @property
    def quote_id(self) -> str:
        # Deterministic identifier for logs/selection; cheap and local
        base = (self.resolver_id, self.kind, self.cost, self.label, str(self.existing_uid or ""))
        return "|".join(map(str, base))

# ---------- Ticket ----------

ProvisionTicketStatus = Literal["new", "pending", "bound", "skipped", "unsat"]

@dataclass
class ProvisionTicket:
    """
    Tracks the lifecycle of satisfying a requirement (or accepting an attachment).
    Not intended for persistence with callables; persist only ids/status if needed.
    """
    status: ProvisionTicketStatus = "new"
    proposal_offers: list[ProvisionOffer] = field(default_factory=list)
    accepted_offer: Optional[ProvisionOffer] = None
    bound_uid: Optional[UUID] = None
    requirer_uid: Optional[UUID] = None        # the owner/anchor node
    requirement_uid: Optional[UUID] = None     # the requirement node on-graph
    corr_id: Optional[str] = None              # async correlation (media, IO)
    error: Optional[str] = None
