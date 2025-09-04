# tangl/vm/frontier.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Literal, List, Optional
from uuid import UUID

from tangl.core36.graph import Graph
from tangl.core36.facts import Facts
from tangl.vm36.execution.tick import StepContext
from .provision import Provisioner
from .offers import Offer, OfferProvider, ensure_attachment_marker, _StaticOfferProvider

Status = Literal["enabled", "pending", "blocked"]


@dataclass
class TemplateRegistry:
    providers: List[OfferProvider] = field(default_factory=list)

    def register(self, p) -> None:
        """
        Register either a provider or offer/specs.

        Accepts:
          - provider with `.enumerate(...)`
          - single Offer / Offer
          - list/tuple of Offer / Offer
          - list/tuple of dicts with at least `id` and `label` keys (will be converted)
        """
        def _is_offerlike(x):
            if Offer is not None and isinstance(x, Offer):
                return True
            if Offer is not None and isinstance(x, Offer):
                return True
            # duck-type minimal keys for dicts
            if isinstance(x, dict) and {"id", "label"}.issubset(x.keys()):
                return True
            return False

        def _to_offer(x):
            if Offer is not None and isinstance(x, Offer):
                return x
            if Offer is not None and isinstance(x, Offer):
                return x
            if isinstance(x, dict):
                # Convert dict → Offer; map `requires` through as-is.
                # Fallback to mode="transition" if not specified.
                mode = x.get("mode", "transition")
                requires = x.get("requires", [])
                guard = x.get("guard", (lambda g, f, c, a: True))
                produce = x.get("produce", (lambda c, a: None))
                # Construct Offer if available; otherwise fall back to Offer
                if Offer is not None:
                    return Offer(
                        id=x["id"], label=x["label"], mode=mode,
                        priority=x.get("priority", 50), source_uid=x.get("source_uid"),
                        guard=guard, requires=requires, produce=produce,
                    )
                if Offer is not None:
                    return Offer(
                        id=x["id"], label=x["label"], priority=x.get("priority", 50),
                        guard=guard, requires=requires, produce=produce,
                    )
            return None

        if hasattr(p, "enumerate"):
            self.providers.append(p)
            return

        if _is_offerlike(p):
            spec = _to_offer(p)
            if spec is None:
                raise TypeError("Could not convert offer-like object to spec")
            self.providers.append(_StaticOfferProvider((spec,)))
            return

        if isinstance(p, (list, tuple)) and all(_is_offerlike(x) for x in p):
            specs = tuple(_to_offer(x) for x in p)
            self.providers.append(_StaticOfferProvider(specs))
            return

        raise TypeError(
            f"TemplateRegistry.register expected a provider or Offer/Offer(s); got {type(p).__name__}"
        )

    def collect(self, g: Graph, facts: Facts, ctx: StepContext, anchor_uid: UUID) -> list[Offer]:
        specs: list[Offer] = []
        for p in self.providers:
            specs.extend(p.enumerate(g, facts, ctx, anchor_uid))
        specs.sort(key=lambda s: (s.priority, s.id))
        return specs

def collect_offers_from_scope(scope, g, facts, ctx, anchor_uid):
    specs = []
    for p in scope.offer_providers:
        specs.extend(p.enumerate(g, facts, ctx, anchor_uid))
    specs.sort(key=lambda s: (s.priority, s.id))
    return specs

# -------- Feasibility check (no mutation) ------------------------------------

@dataclass(frozen=True)
class Choice:
    id: str
    label: str
    status: Status
    reason: Optional[str]
    # Partially-applied executor we can call during EXECUTE to realize + produce
    execute: Callable[[StepContext], None]

def _quick_feasibility(g, facts, ctx, anchor_uid, spec, *, scope) -> tuple[Status, Optional[str]]:
    pending = False
    resolvers_by_kind = getattr(scope, "resolvers_by_kind", {}) or {}

    for req in spec.requires:
        pol = req.policy or {}
        optional   = bool(pol.get("optional", False))
        prune      = bool(pol.get("prune_if_unsatisfied", True))
        create_ok  = bool(pol.get("create_if_missing", False))

        resolvers = list(resolvers_by_kind.get(req.kind, ()))
        any_existing = False
        any_creatable = False

        for r in resolvers:
            try:
                for q in (r.propose(g, facts, anchor_uid, req) or ()):  # proposal-style
                    # If the quote has a guard, it must pass
                    q_guard = getattr(q, "guard", None)
                    if q_guard is not None and not q_guard(g, facts, ctx, anchor_uid):
                        continue
                    if getattr(q, "existing_uid", None) is not None:
                        any_existing = True
                    else:
                        any_creatable = True
            except Exception:
                # Keep feasibility resilient; individual resolver errors shouldn't break planning
                continue

        if any_existing or (create_ok and any_creatable):
            # This requirement is satisfiable now
            continue

        if optional or not prune:
            pending = True
            continue

        return "blocked", f"requirement {req.kind}:{req.name} unsatisfied"

    return ("pending", None) if pending else ("enabled", None)


# -------- Discovery entry point ----------------------------------------------
def discover_frontier(ctx, *, anchor_uid):
    g = ctx.preview(); facts = Facts.compute(g)
    scope = getattr(ctx, "scope", None)
    if scope is None:
        from tangl.vm36.scoping.scope import Scope
        scope = Scope(
            ns=ctx.ns,
            handlers=[(ph, hid, prio, fn) for ph, lst in (ctx.scope_handlers or {}).items() for (prio, hid, fn) in lst],
            offer_providers=getattr(ctx, "scope_templates", []),
            resolvers_by_kind=getattr(getattr(ctx, "bundle", None), "resolvers_by_kind", {}),
            active_domains=getattr(ctx, "active_domains", set()),
            cursor_uid=ctx.cursor_uid,
            cursor_label=ctx.cursor_label,
        )
        ctx.scope = scope

    specs = collect_offers_from_scope(scope, g, facts, ctx, anchor_uid)

    out = []
    for spec in specs:
        if not spec.guard(g, facts, ctx, anchor_uid):
            out.append(Choice(spec.id, spec.label, "blocked", "guard", execute=lambda c: None))
            continue

        status, reason = _quick_feasibility(g, facts, ctx, anchor_uid, spec, scope=scope)

        def _exec(spec=spec, scope=scope):
            def run(c):
                prov = Provisioner.from_scope(scope)
                for r in spec.requires:
                    prov.require(c, anchor_uid, r)
                if spec.mode == "attachment":
                    created = ensure_attachment_marker(c, anchor_uid, spec.id, source_uid=spec.source_uid)
                    if not created:
                        return
                    spec.produce(c, anchor_uid)
                else:
                    spec.produce(c, anchor_uid)
            return run

        out.append(Choice(spec.id, spec.label, status, reason, execute=_exec()))
    ctx.enabled_choices = out
    return out
