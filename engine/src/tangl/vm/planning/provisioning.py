# tangl/vm/provisioning.py
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
from typing import Optional

from pydantic import Field

from tangl.type_hints import StringMap, Identifier, UnstructuredData
from tangl.core import Node, Registry, Entity
from tangl.core.entity import Selectable
from .requirement import Requirement, ProvisioningPolicy

class Provisioner(Selectable, Entity):
    """
    Provisioner(requirement, registries=[graph, ...])

    Default provider resolver for requirements.

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
    * **Failure handling** – marks :attr:`Requirement.is_unresolvable` on failure.

    API
    ---
    - :meth:`resolve()` – execute provisioning per policy.
    - :meth:`_resolve_existing()` – locate existing provider.
    - :meth:`_resolve_update()` – mutate in place using template.
    - :meth:`_resolve_clone()` – duplicate and evolve a reference provider.
    - :meth:`_resolve_create()` – instantiate from template.

    Notes
    -----
    On success, the resolved provider is assigned to
    :attr:`Requirement.provider` and added to the graph if missing.
    """
    requirement: Requirement
    registries: list[Registry] = Field(default_factory=list)

    def _resolve_existing(self,
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
        return Registry.chain_find_one(self.requirement.graph, *self.registries, **provider_criteria)

    def _resolve_update(self,
                        provider_id: Optional[Identifier] = None,
                        provider_criteria: Optional[StringMap] = None,
                        update_template: UnstructuredData = None
                        ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, update by template"""
        if update_template is None:
            raise ValueError("UPDATE must include update template")
        provider = self._resolve_existing(provider_id, provider_criteria)
        if not provider:
            return None
        provider.update_attrs(**update_template)
        return provider

    def _resolve_clone(self,
                       ref_id: Optional[Identifier] = None,
                       ref_criteria: Optional[StringMap] = None,
                       update_template: UnstructuredData = None
                       ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, evolve copy by template"""
        if update_template is None:
            raise ValueError("CLONE must include update template")
        ref = self._resolve_existing(ref_id, ref_criteria)
        if not ref:
            return None
        provider = ref.evolve(**update_template)  # todo: ensure NEW uid
        return provider

    def _resolve_create(self, provider_template: UnstructuredData) -> Node:
        """Create successor from template"""
        provider = Node.structure(provider_template)
        return provider

    # todo: this is the fallback for "on_provision", it returns if nothing else does first
    def resolve(self) -> Optional[Node]:
        """Attempt to resolve a provider for the requirement attribs and given policy"""

        provider = None

        match self.requirement.policy:
            case ProvisioningPolicy.EXISTING:
                provider = self._resolve_existing(
                    provider_id=self.requirement.identifier,
                    provider_criteria=self.requirement.criteria,
                )
            case ProvisioningPolicy.UPDATE:
                provider = self._resolve_update(
                    provider_id=self.requirement.identifier,
                    provider_criteria=self.requirement.criteria,
                    update_template=self.requirement.template
                    )
            case ProvisioningPolicy.CLONE:
                provider = self._resolve_clone(
                    ref_id=self.requirement.identifier,
                    ref_criteria=self.requirement.criteria,
                    update_template=self.requirement.template
                    )
            case ProvisioningPolicy.CREATE:
                provider = self._resolve_create(
                    provider_template=self.requirement.template
                    )
            case _:
                raise ValueError(f"Unknown provisioning policy {self.requirement.policy}")

        # todo: If the default provisioner fails, we want to search for role aliases,
        #  alternative creation mechanisms and templates in the scope/namespace;
        #  assume we searched those first and just flag it as unresolvable here in the
        #  ns-free fallback?

        if provider is None:
            self.requirement.is_unresolvable = True
            return None

        self.requirement.provider = provider
        return provider
