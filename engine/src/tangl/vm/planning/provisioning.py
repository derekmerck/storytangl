# tangl/vm/provisioning.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from tangl.type_hints import StringMap, Identifier, UnstructuredData
from tangl.core import Node, Registry
from .requirement import Requirement, ProvisioningPolicy

@dataclass
class Provisioner:
    # Default provisioner for Dependency edges
    # todo: Provisioners need to be implemented like handlers/handler registries, so
    #       that they can be passed around in domains, I think
    #       previously they yielded an offer job receipt with an 'accept' function
    #       for the orchestrator to select

    requirement: Requirement
    registries: list[Registry] = field(default_factory=list)

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
        provider.update(**update_template)
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
