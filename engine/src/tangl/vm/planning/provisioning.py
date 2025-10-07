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
from typing import Optional, Type, TYPE_CHECKING
import functools

from tangl.type_hints import StringMap, Identifier, UnstructuredData
from tangl.core import Node, Registry, Handler, JobReceipt
from .requirement import Requirement, ProvisioningPolicy

if TYPE_CHECKING:
    from .offer import ProvisionOffer


class Provisioner(Handler):
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

    @staticmethod
    def _resolve_existing(registry: Registry,
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
        return Registry.chain_find_one(registry, **provider_criteria)

    @staticmethod
    def _resolve_update(registry: Registry,
                        provider_id: Optional[Identifier] = None,
                        provider_criteria: Optional[StringMap] = None,
                        update_template: UnstructuredData = None
                        ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, update by template"""
        if update_template is None:
            raise ValueError("UPDATE must include update template")
        if 'graph' in update_template:
            raise KeyError("Update template may not include 'graph' key")
        provider = Provisioner._resolve_existing(registry, provider_id, provider_criteria)
        if not provider:
            return None
        provider.update_attrs(**update_template)
        return provider

    @staticmethod
    def _resolve_clone(registry: Registry,
                       ref_id: Optional[Identifier] = None,
                       ref_criteria: Optional[StringMap] = None,
                       update_template: UnstructuredData = None
                       ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, evolve copy by template"""
        if update_template is None:
            raise ValueError("CLONE must include update template")
        if 'graph' in update_template:
            raise KeyError("Update template may not include 'graph' key")
        ref = Provisioner._resolve_existing(registry, ref_id, ref_criteria)
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

    def get_offers(self, requirement: Requirement) -> list[ProvisionOffer]:
        from .offer import ProvisionOffer

        offers: list[ProvisionOffer] = []

        # check for extant
        extant = False
        if (requirement.policy is not ProvisioningPolicy.CREATE and
                (requirement.identifier or requirement.criteria)):
            extant = self._resolve_existing(
                registry=requirement.registry,
                provider_id=requirement.identifier,
                provider_criteria=requirement.criteria,
            )
        has_template = requirement.template is not None

        for policy in requirement.policy:
            offer_cb = None
            offer_policy = None
            match policy:
                case ProvisioningPolicy.EXISTING if extant:
                    # doesn't like assigned lambdas?
                    offer_cb = functools.partial(
                        self._resolve_existing,
                        registry=requirement.graph,
                        provider_id=extant.uid
                    )
                    offer_policy = ProvisioningPolicy.EXISTING
                case ProvisioningPolicy.UPDATE if extant and has_template:
                    offer_cb = functools.partial(
                        self._resolve_update,
                        registry=requirement.graph,
                        provider_id=extant.uid,
                        update_template=requirement.template
                    )
                    offer_policy = ProvisioningPolicy.UPDATE
                case ProvisioningPolicy.CLONE if extant and has_template:
                    offer_cb = functools.partial(
                        self._resolve_clone,
                        registry=requirement.graph,
                        ref_id=extant.uid,
                        update_template=requirement.template
                        )
                    offer_policy = ProvisioningPolicy.CLONE
                case ProvisioningPolicy.CREATE if has_template:
                    offer_cb = functools.partial(
                        self._resolve_create,
                        registry = requirement.graph,
                        provider_template=requirement.template
                        )
                    offer_policy = ProvisioningPolicy.CREATE
                case _:
                    pass
                    # raise ValueError(f"Unknown provisioning policy {self.requirement.policy}")

            if offer_cb is not None:
                offer = ProvisionOffer(
                    requirement=requirement,
                    provisioner=self,
                    accept_func=offer_cb,
                    operation=offer_policy,
                )
                offers.append(offer)

        return offers

    def __call__(self, requirement: Requirement, *args, **kwargs) -> JobReceipt:
        offers = self.get_offers(requirement=requirement)
        return JobReceipt(
            blame_id=self.uid,
            caller_id=requirement.uid,
            result=offers,
            result_type=self.result_type,
        )

    def resolve(self, requirement: Requirement) -> Optional[Node]:
        """Return a provider for ``requirement`` or ``None`` without side effects."""

        provider = None

        match requirement.policy:
            case ProvisioningPolicy.EXISTING:
                provider = self._resolve_existing(
                    registry=requirement.graph,
                    provider_id=requirement.identifier,
                    provider_criteria=requirement.criteria,
                )
            case ProvisioningPolicy.UPDATE:
                provider = self._resolve_update(
                    registry=requirement.graph,
                    provider_id=requirement.identifier,
                    provider_criteria=requirement.criteria,
                    update_template=requirement.template
                    )
            case ProvisioningPolicy.CLONE:
                provider = self._resolve_clone(
                    registry=requirement.graph,
                    ref_id=requirement.identifier,
                    ref_criteria=requirement.criteria,
                    update_template=requirement.template
                    )
            case ProvisioningPolicy.CREATE:
                provider = self._resolve_create(
                    registry=requirement.graph,
                    provider_template=requirement.template
                    )
            case _:
                raise ValueError(f"Unsupported provisioning policy {requirement.policy}")

        return provider
