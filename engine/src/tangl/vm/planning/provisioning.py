# tangl/vm/planning/provisioning.py
"""
Provisioning logic
==================

Why
----
Provides the default :class:`Provisioner`, responsible for satisfying a
:class:`~tangl.vm.planning.requirement.Requirement` by locating or constructing
a provider node.  It searches across one or more registries, updating or
cloning existing nodes, or creating a new one from a template when needed.

Key Features
------------
* **Multiple acquisition modes** – EXISTING, UPDATE, CLONE, CREATE.
* **Graph integration** – discovered or built providers are bound to the
  requirement and inserted into the active graph.
* **Extensible** – domains may subclass or replace this implementation to
  add scope‑aware provisioning, aliases, or custom creation pipelines.

API
---
- :class:`Provisioner` – default resolver for requirements.
- :meth:`Provisioner.resolve` – main entry point; dispatches by policy.
- :meth:`_resolve_existing` / :meth:`_resolve_update` / :meth:`_resolve_clone` / :meth:`_resolve_create` – internal helpers implementing each policy.
"""
from __future__ import annotations
from typing import Iterable, Optional, Sequence, Type, TYPE_CHECKING
import functools

from tangl.type_hints import StringMap, Identifier, UnstructuredData
from tangl.core import Node, Registry, Behavior, CallReceipt
from tangl.core.dispatch.behavior import HandlerType
from .requirement import Requirement, ProvisioningPolicy

if TYPE_CHECKING:
    from .offer import ProvisionOffer
    from ..context import Context


class Provisioner(Behavior):
    """
    Default provider resolver for independently satisfiable requirements.

    Why
    ----
    Attempts to fulfill a :class:`~tangl.vm.planning.requirement.Requirement`
    by applying the policy specified in its :attr:`Requirement.policy`.  Each
    policy corresponds to a helper that locates, mutates, clones, or constructs
    a provider node.

    Key Features
    ------------
    * **Policy‑driven** – delegates to helpers matching :class:`ProvisioningPolicy`.
    * **Registry search** – uses :meth:`~tangl.core.registry.Registry.chain_find_one`
      across provided registries and the graph.
    * **Template application** – UPDATE/CLONE/CREATE use the requirement’s
      :attr:`Requirement.template` to modify or instantiate nodes.
    * **Pure resolution** – :meth:`resolve` returns providers without mutating
      requirements; callers decide how to handle success or failure.

    API
    ---
    - :meth:`resolve()` – execute provisioning per policy and return a provider or ``None``.
    - :meth:`_resolve_existing()` – locate existing provider.
    - :meth:`_resolve_update()` – mutate in place using template.
    - :meth:`_resolve_clone()` – duplicate and evolve a reference provider.
    - :meth:`_resolve_create()` – instantiate from template.

    """
    phase: str = "PLANNING.OFFER"
    result_type: Type = list['ProvisionOffer']
    func: None = None
    handler_type: HandlerType = HandlerType.INSTANCE_ON_OWNER

    @staticmethod
    def _resolve_existing(*registries: Registry,
                          provider_id: Optional[Identifier] = None,
                          provider_criteria: Optional[StringMap] = None) -> Optional[Node]:
        """Find successor by reference and filter by criteria"""
        # todo: do we want to check that it's available in the current ns?  We don't include the ns in the sig?
        provider_criteria = provider_criteria or {}
        if provider_id is not None:
            # clobber existing if given
            # Entity.has_identifier(x) will match uid, get_label(), and short_uid() by default
            # for subclasses, it also matches fields tagged with "is_identifier" or methods
            # annotated with meth._is_identifier = True
            provider_criteria['has_identifier'] = provider_id
        if not provider_criteria:
            raise ValueError("Must include some provider id or criteria")
        registries = [r for r in registries if r is not None]
        if not registries:
            raise ValueError("Must include at least one registry to search")
        return Registry.chain_find_one(*registries, **provider_criteria)

    @staticmethod
    def _resolve_update(*registries: Registry,
                        provider_id: Optional[Identifier] = None,
                        provider_criteria: Optional[StringMap] = None,
                        update_template: UnstructuredData = None
                        ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, update by template"""
        if update_template is None:
            raise ValueError("UPDATE must include update template")
        if 'graph' in update_template:
            raise KeyError("Update template may not include 'graph' key")
        provider = Provisioner._resolve_existing(*registries,
                                                provider_id=provider_id,
                                                provider_criteria=provider_criteria)
        if not provider:
            return None
        provider.update_attrs(**update_template)
        return provider

    @staticmethod
    def _resolve_clone(*registries: Registry,
                       ref_id: Optional[Identifier] = None,
                       ref_criteria: Optional[StringMap] = None,
                       update_template: UnstructuredData = None
                       ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, evolve copy by template"""
        if update_template is None:
            raise ValueError("CLONE must include update template")
        if 'graph' in update_template:
            raise KeyError("Update template may not include 'graph' key")
        ref = Provisioner._resolve_existing(*registries,
                                            provider_id=ref_id,
                                            provider_criteria=ref_criteria)
        if not ref:
            return None
        provider = ref.evolve(**update_template)  # todo: ensure NEW uid, graph says the same
        return provider

    @staticmethod
    def _resolve_create(registry: Registry, provider_template: UnstructuredData) -> Node:
        """Create successor from template"""
        if 'graph' in provider_template:
            raise KeyError("Provider template may not include 'graph' key")
        provider = Node.structure(provider_template)
        registry.add(provider)
        return provider

    def _requirement_registries(self, requirement: Requirement) -> tuple[Registry, ...]:
        registries: list[Registry] = []
        if isinstance(getattr(requirement, "graph", None), Registry):
            registries.append(requirement.graph)
        extra_registry = getattr(requirement, "registry", None)
        if isinstance(extra_registry, Registry):
            registries.append(extra_registry)
        elif isinstance(extra_registry, Iterable):
            registries.extend([r for r in extra_registry if isinstance(r, Registry)])
        return tuple(registries)

    def iter_requirement_registries(
        self,
        requirement: Requirement,
        *,
        ctx: "Context" | None = None,
    ) -> tuple[Registry, ...]:
        """Return registries to search while evaluating ``requirement``.

        Subclasses may override to inject additional registries derived from the
        active :class:`~tangl.vm.context.Context`.
        """

        registries = list(self._requirement_registries(requirement))
        if ctx is not None:
            context_graph = getattr(ctx, "graph", None)
            if context_graph is not None and all(r is not context_graph for r in registries):
                registries.insert(0, context_graph)
        return tuple(registries)

    @staticmethod
    def _iter_policies(policy: ProvisioningPolicy) -> Sequence[ProvisioningPolicy]:
        if policy in (
            ProvisioningPolicy.EXISTING,
            ProvisioningPolicy.UPDATE,
            ProvisioningPolicy.CREATE,
            ProvisioningPolicy.CLONE,
        ):
            return (policy,)
        policies: list[ProvisioningPolicy] = []
        for candidate in ProvisioningPolicy:
            if candidate in (ProvisioningPolicy.NOOP, ProvisioningPolicy.ANY):
                continue
            if candidate in policy:
                policies.append(candidate)
        return tuple(policies)

    def get_offers(
        self,
        requirement: Requirement,
        *,
        ctx: "Context" | None = None,
    ) -> list[ProvisionOffer]:
        from .offer import ProvisionOffer

        registries = self.iter_requirement_registries(requirement, ctx=ctx)
        offers: list[ProvisionOffer] = []

        extant: Optional[Node] = None
        if requirement.identifier or requirement.criteria:
            try:
                extant = self._resolve_existing(
                    *registries,
                    provider_id=requirement.identifier,
                    provider_criteria=requirement.criteria,
                )
            except ValueError:
                extant = None

        has_template = requirement.template is not None

        for policy in self._iter_policies(requirement.policy):
            accept_cb = None
            match policy:
                case ProvisioningPolicy.EXISTING if extant is not None:
                    accept_cb = functools.partial(
                        self._resolve_existing,
                        *registries,
                        provider_id=extant.uid,
                    )
                case ProvisioningPolicy.UPDATE if extant is not None and has_template:
                    accept_cb = functools.partial(
                        self._resolve_update,
                        *registries,
                        provider_id=extant.uid,
                        update_template=requirement.template,
                    )
                case ProvisioningPolicy.CLONE if extant is not None and has_template:
                    accept_cb = functools.partial(
                        self._resolve_clone,
                        *registries,
                        ref_id=extant.uid,
                        update_template=requirement.template,
                    )
                case ProvisioningPolicy.CREATE if has_template and registries:
                    accept_cb = functools.partial(
                        self._resolve_create,
                        registries[0],
                        requirement.template,
                    )
                case _:
                    continue

            offers.append(
                ProvisionOffer(
                    requirement=requirement,
                    provisioner=self,
                    accept_func=accept_cb,
                    operation=policy,
                )
            )

        return offers

    def __call__(
        self,
        requirement: Requirement,
        *args,
        **kwargs,
    ) -> CallReceipt:
        ctx: "Context" | None = kwargs.get("ctx")
        offers = self.get_offers(requirement=requirement, ctx=ctx)
        return CallReceipt(
            blame_id=self.uid,
            caller_id=requirement.uid,
            result=offers,
            result_type=self.result_type,
        )

    def resolve(
        self,
        requirement: Requirement,
        *,
        ctx: "Context" | None = None,
    ) -> Optional[Node]:
        """Return a provider for ``requirement`` or ``None`` without side effects."""

        provider = None

        registries = self.iter_requirement_registries(requirement, ctx=ctx)

        match requirement.policy:
            case ProvisioningPolicy.EXISTING:
                provider = self._resolve_existing(
                    *registries,
                    provider_id=requirement.identifier,
                    provider_criteria=requirement.criteria,
                )
            case ProvisioningPolicy.UPDATE:
                provider = self._resolve_update(
                    *registries,
                    provider_id=requirement.identifier,
                    provider_criteria=requirement.criteria,
                    update_template=requirement.template
                    )
            case ProvisioningPolicy.CLONE:
                provider = self._resolve_clone(
                    *registries,
                    ref_id=requirement.identifier,
                    ref_criteria=requirement.criteria,
                    update_template=requirement.template
                    )
            case ProvisioningPolicy.CREATE:
                registry = registries[0] if registries else requirement.graph
                provider = self._resolve_create(
                    registry,
                    requirement.template
                    )
            case _:
                raise ValueError(f"Unsupported provisioning policy {requirement.policy}")

        return provider
