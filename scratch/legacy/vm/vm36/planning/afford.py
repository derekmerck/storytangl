# tangl/vm/afford.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
from tangl.vm36.planning.offers import ensure_attachment_marker, Offer
from tangl.vm36.planning.provision import Provisioner

@dataclass
class AffordanceRegistry:
    """Holds providers that enumerate attachment offers."""
    providers: list = field(default_factory=list)
    def register(self, provider) -> None:
        self.providers.append(provider)
    def enumerate(self, g, facts, ctx, anchor_uid) -> Iterable[Offer]:
        for p in self.providers:
            yield from p.enumerate(g, facts, ctx, anchor_uid)

def enable_affordances(ctx, areg: AffordanceRegistry, *, anchor_uid):
    """
    Execute all eligible attachment offers from affordance providers.
    - Uses ctx.preview() for read-your-writes dedup.
    - Provisions any requirements (tickets are non-blocking unless policy says otherwise).
    - Adds the affordance marker edge; produce() runs only once per offer per tick.
    """
    g = ctx.preview()
    facts = ctx.facts
    # Use resolvers mounted on the scope
    prov = Provisioner.from_scope(getattr(ctx, "scope", None))

    for offer in areg.enumerate(g, facts, ctx, anchor_uid):
        if getattr(offer, "mode", "transition") != "attachment":
            continue
        if not offer.guard(g, facts, ctx, anchor_uid):
            continue

        # Provision any requirements declared by this affordance
        for req in getattr(offer, "requires", ()) or ():
            # Returns ProvisionOutcome; we don't gate enablement here—affordances are
            # allowed to be non-blocking (tickets can remain pending/unsat by policy).
            prov.require(ctx, anchor_uid, req)

        # Dedup per tick using the PREVIEW graph
        created = ensure_attachment_marker(
            ctx, anchor_uid, offer.id, source_uid=getattr(offer, "source_uid", None)
        )
        if not created:
            continue

        # Perform the side-effect once
        offer.produce(ctx, anchor_uid)
