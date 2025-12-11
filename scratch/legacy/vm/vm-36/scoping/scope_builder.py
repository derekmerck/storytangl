from __future__ import annotations
from dataclasses import dataclass, field
from collections import ChainMap, defaultdict
from typing import Callable, Mapping, Dict, List, Set, TYPE_CHECKING, Any
from uuid import UUID

from tangl.core36 import Graph, Node, Facts
from tangl.vm36.execution import StepContext, Phase
from tangl.vm36.planning import GenericEntityBuilder, GenericEntityFinder
from tangl.vm36.planning.resolver import SimpleRoleResolver
from tangl.vm36.planning.offers import OfferProvider, _StaticOfferProvider
from .domains import DomainRegistry

if TYPE_CHECKING:
    from tangl.vm36.execution import StepContext, Phase
    from tangl.vm36.planning import OfferProvider
    from .scope import Scope
# --- Offer/provider normalization helpers ---

def _as_offer(obj):
    """Convert dict/Offer to a concrete Offer or return None."""
    try:
        from tangl.vm36.planning.offers import Offer as _Offer
    except Exception:
        return None
    if isinstance(obj, _Offer):
        return obj
    if isinstance(obj, dict) and {"id", "label"}.issubset(obj.keys()):
        return _Offer(
            id=obj["id"],
            label=obj["label"],
            mode=obj.get("mode", "transition"),
            priority=obj.get("priority", 50),
            source_uid=obj.get("source_uid"),
            guard=obj.get("guard", (lambda g, f, c, a: True)),
            requires=obj.get("requires", []),
            produce=obj.get("produce", (lambda c, a: None)),
        )
    return None


def _provider_from(obj):
    """Normalize a domain/structural contribution into an OfferProvider or None.
    Accepts:
      - an object with enumerate(...)
      - a single Offer or dict
      - a list/tuple of Offers or dicts
    """
    if obj is None:
        return None

    # Already a provider
    if hasattr(obj, "enumerate"):
        return obj

    # Sequence of offers/dicts
    if isinstance(obj, (list, tuple)):
        offs = []
        for t in obj:
            off = _as_offer(t)
            if off is not None:
                offs.append(off)
        return _StaticOfferProvider(tuple(offs)) if offs else None

    # Single offer/dict
    off = _as_offer(obj)
    if off is not None:
        return _StaticOfferProvider((off,))

    return None


class ScopeBuilder:

    def __init__(self, g: Graph, facts: Facts, cursor_uid: UUID,
                 domains: DomainRegistry | None = None,
                 globals_ns: Mapping[str, object] | None = None):

        # instance vars
        self.g = g
        self.facts = facts
        self.anchor = cursor_uid
        self.domains = domains
        self.globals_ns = globals_ns

        # working vars
        self.active_domains: set[str] = set()
        self.ns_layers: List[Mapping[str, Any]] = []
        self.handlers: List[tuple] = []
        self.offer_providers: List[OfferProvider] = []
        self.resolvers_by_kind: Dict[str, List[object]] = {}

    # todo: it seems like anchor.local is just another domain that might carry any capability, should we assemble by domain by capability instead of by capability by source?

    # 1) locals on the node
    def add_node_locals(self):
        n = self.g.get(self.anchor)
        if getattr(n, "locals", None):
            self.ns_layers.append(n.locals)

    # 2) alias/role bindings
    def add_bindings_layer(self):
        # todo: include this when implemented
        # self.ns_layers.append(BindingNamespace(self.g, self.anchor))
        pass

    # 3) ancestor locals (nearest first → lower precedence)
    def add_ancestor_locals(self):
        for uid in self.facts.ancestors(self.anchor):
            n = self.g.get(uid)
            if getattr(n, "locals", None):
                self.ns_layers.append(n.locals)

    # 4) domains (flat for MVP; your DomainRegistry can still supply vars/handlers/providers/templates])
    def add_domains(self):
        # 1) gather active domain names from tags along ancestors
        self.active_domains = self.facts.active_domains_along(self.anchor)
        if not self.domains:
            return

        # 2) expand via inheritance and linearize: parent-before-child
        ordered_domains = self.domains.linearize(self.active_domains) or []

        # 3) collect domain vars/handlers/templates for the ANCHOR NODE
        node = self.g.get(self.anchor)

        for dname in ordered_domains:
            # vars
            try:
                dvars = self.domains._vars(dname, self.g, node)
                if dvars:
                    self.ns_layers.append(dvars)
            except Exception:
                pass

            # handlers
            try:
                dhandlers = self.domains._handlers(dname, self.g, node)
                if dhandlers:
                    self.handlers.extend(dhandlers)
            except Exception:
                pass

            # templates → provider
            try:
                dtemplates = self.domains._templates(dname, self.g, node)
            except Exception:
                dtemplates = None
            prov = _provider_from(dtemplates)
            if prov:
                self.offer_providers.append(prov)

            # optional: domain-provided resolvers
            try:
                dresolvers = getattr(self.domains, "_resolvers", None)
                if callable(dresolvers):
                    by_kind = dresolvers(dname, self.g, node) or {}
                    for k, lst in by_kind.items():
                        self.resolvers_by_kind.setdefault(k, []).extend(lst)
            except Exception:
                pass

    def add_structural_templates(self):
        # Ancestor templates (closest first)
        try:
            for aid in self.facts.ancestors(self.anchor):
                a = self.g.get(aid)
                if getattr(a, "locals", None):
                    prov = _provider_from(a.locals.get("templates"))
                    if prov:
                        self.offer_providers.append(prov)
        except Exception:
            pass

        # Current-node templates
        try:
            n = self.g.get(self.anchor)
            if getattr(n, "locals", None):
                prov = _provider_from(n.locals.get("templates"))
                if prov:
                    self.offer_providers.append(prov)
        except Exception:
            pass

    # 5) defaults (global + generic resolvers)
    def add_defaults(self):
        # todo: global ns vars, handlers, resolvers should be in the globals domain
        #       default ns vars, etc should be in a defaults domain and handled by
        #       the same add-domain-capabilities mechanism

        # Global vars (e.g., version)
        from tangl import __version__
        self.ns_layers.append({"__tangl__": {"version": __version__}})

        if self.globals_ns:
            self.ns_layers.append(self.globals_ns)

        # Generic resolvers available everywhere
        self.resolvers_by_kind.setdefault("entity", []).extend([GenericEntityFinder(), GenericEntityBuilder()])
        self.resolvers_by_kind.setdefault("role", []).extend([SimpleRoleResolver()])

    # 6) pack into Scope
    def build(self) -> "Scope":
        self.add_node_locals()
        self.add_bindings_layer()  # no-op until BindingNamespace is wired
        self.add_ancestor_locals()
        self.add_domains()
        self.add_structural_templates()
        self.add_defaults()

        # ChainMap resolves left→right, so keep insertion order:
        #   node locals → ancestor locals → domain vars → globals
        ns = ChainMap(*self.ns_layers) if self.ns_layers else ChainMap({})
        from .scope import Scope
        return Scope(
            ns=ns,
            handlers=self.handlers,
            offer_providers=self.offer_providers,
            resolvers_by_kind=self.resolvers_by_kind,
            active_domains=self.active_domains,
            cursor_uid=self.anchor,
            cursor_label=getattr(self.g.get(self.anchor), "label", None),
        )

    # Optional: add_offer_providers / add_handlers hooks if you integrate DomainRegistry later

    @classmethod
    def assemble(cls, g: Graph, facts: Facts, cursor_uid: UUID, domains, globals_ns) -> Scope:
        b = cls(g, facts, cursor_uid, domains=domains, globals_ns=globals_ns)
        return b.build()
#
# def refresh_scope_for_phase(
#     ctx: StepContext,
#     domains: DomainRegistry,
#     globals_ns: Mapping[str, object] | None = None,
# ) -> None:
#     """Recompute scope against preview graph and the effective cursor (read-your-writes)."""
#     g = ctx.preview() if ctx.graph is not None else None
#     cur = ctx.effective_cursor()
#     if not (g and cur):
#         return
#     pfacts = Facts.compute(g)
#     scope = ScopeBuilder.assemble(g, pfacts, cur, domains=domains, globals_ns=globals_ns)
#     node = g.get(cur)
#     label = getattr(node, "label", None) if node else None
#     ctx.mount_scope(scope)
