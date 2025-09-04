# tangl/vm/offers.py
from dataclasses import dataclass, field
from typing import Callable, Literal, Protocol, Iterable, Optional
from uuid import UUID

from tangl.core36 import Graph, Facts
from tangl.core36.types import EdgeKind
from tangl.core36.facts import Facts
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.planning.ticket import ProvisionRequirement

Mode = Literal["transition", "attachment"]

@dataclass(frozen=True)
class Offer:
    """
    Declarative next-step option anchored at `anchor_uid` (the cursor).
    - id:        stable identifier for dedup/audit
    - label:     short UI label / human-friendly
    - priority:  sort order (lower first) for stable presentation
    - guard:     (g, facts, ctx, anchor_uid) -> bool  (precondition to even consider)
    - requires:  requirements that must be satisfiable to enable
    - produce:   (ctx, anchor_uid) -> None  (emits Effects when this choice is EXECUTED)
    """
    id: str
    label: str
    mode: Literal["transition", "attachment"] = "transition"
    priority: int = 50
    source_uid: Optional[UUID] = None
    guard: Callable[[Graph, Facts, StepContext, UUID], bool] = lambda *_: True
    requires: list[ProvisionRequirement] = field(default_factory=list)
    produce: Callable[[StepContext, UUID], None] = lambda *_: None

    @property
    def is_affordance(self) -> bool:
        return self.mode == "attachment"


class OfferProvider(Protocol):
    def enumerate(self, g, facts, ctx, anchor_uid) -> Iterable[Offer]: ...


class _StaticOfferProvider:
    """Wrap one or more Offer objects as a OfferProvider."""

    def __init__(self, specs: tuple[Offer, ...]):
        self._specs = specs

    def enumerate(self, g: Graph, facts: Facts, ctx: StepContext, anchor_uid: UUID):
        return self._specs


def ensure_attachment_marker(ctx, anchor_uid, offer_id, source_uid=None) -> bool:
    """
    Ensure we have a (source -> anchor) afford marker edge for this attachment offer.
    Returns True if we created it now (i.e., not previously enabled).
    Checks the PREVIEW graph so repeated executes within the same tick are deduped.
    """
    g2 = ctx.preview()  # read-your-writes
    src = source_uid or anchor_uid
    kind = f"{EdgeKind.AFFORD.prefix()}{offer_id}"
    if g2.find_edge_ids(src=src, dst=anchor_uid, kind=kind):
        return False
    ctx.add_edge(src, anchor_uid, kind)
    return True

