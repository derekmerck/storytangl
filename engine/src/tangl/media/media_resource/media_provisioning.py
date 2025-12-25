from __future__ import annotations

from typing import Iterator, Optional

from tangl.type_hints import UnstructuredData
from pydantic import ConfigDict, Field

from tangl.core import BehaviorRegistry
from tangl.vm.provision import DependencyOffer, ProvisionCost, Provisioner
from tangl.vm.provision.provisioning_policy import ProvisioningPolicy
from tangl.vm.provision.requirement import Requirement
from tangl.media.type_hints import Media
from tangl.media.media_creators.media_spec import MediaSpec
from tangl.media.media_data_type import MediaDataType
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from .media_resource_registry import MediaResourceRegistry

on_provision_media = BehaviorRegistry(label="provision_media")


class MediaProvisioner(Provisioner):
    """Provisioner for media dependencies using inline data or specs."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirement: Requirement
    registries: list[MediaResourceRegistry] = Field(default_factory=list)

    def _resolve_existing(self, requirement: Requirement) -> MediaRIT | None:
        identifier = requirement.identifier
        criteria = requirement.criteria or {}
        for registry in self.registries:
            if identifier is not None:
                rit = registry.find_one(has_identifier=identifier)
                if rit:
                    return rit
            if "content_hash" in criteria:
                rit = registry.find_one(content_hash=criteria["content_hash"])
                if rit:
                    return rit
        return None

    def _resolve_update(self, *args, **kwargs):
        raise NotImplementedError("Media UPDATE not implemented")

    def _resolve_clone(self, *args, **kwargs):
        raise NotImplementedError("Media CLONE not implemented")

    def _resolve_create(self, provider_template: UnstructuredData) -> MediaRIT:
        """Create :class:`MediaRIT` from inline data or a spec template."""

        if "data" in provider_template:
            data = provider_template["data"]  # type: Media
            provider = MediaRIT(data=data, data_type=MediaDataType.OTHER)
        elif "spec" in provider_template:
            spec = provider_template["spec"]  # type: MediaSpec
            if hasattr(spec, "adapt_spec"):
                adapted_spec = spec.adapt_spec(self.requirement.reference)
                media, revised_spec = adapted_spec.create_media()
                provider = MediaRIT(data=media, data_type=MediaDataType.OTHER)
                provider.tags.add("spec")
                provider.tags.add(adapted_spec.__class__.__name__)
                provider.data = media
            else:
                raise ValueError("Media spec templates must implement adapt_spec/create_media")
        else:
            raise ValueError("Media CREATE requires either data or spec")

        if not self.registries:
            return provider
        self.registries[0].add(provider)
        return provider

    def get_dependency_offers(
        self, requirement: Requirement, *, ctx: "Context"
    ) -> Iterator[DependencyOffer]:
        if not requirement.policy & ProvisioningPolicy.ANY:
            return

        if existing := self._resolve_existing(requirement):
            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.EXISTING,
                base_cost=ProvisionCost.DIRECT,
                cost=float(ProvisionCost.DIRECT),
                proximity=0.0,
                proximity_detail="media_existing",
                accept_func=lambda _ctx: existing,
                provider_id=existing.uid,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
            )
            return

        template = requirement.template or {}
        if not template:
            return

        def _accept(context: "Context") -> MediaRIT:
            return self._resolve_create(template)

        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=ProvisioningPolicy.CREATE_TEMPLATE,
            base_cost=ProvisionCost.CREATE,
            cost=float(ProvisionCost.CREATE),
            proximity=999.0,
            proximity_detail="media_create",
            accept_func=_accept,
            source_provisioner_id=self.uid,
            source_layer=self.layer,
        )

    def generate_offers(self, *, ctx: "Context") -> list[DependencyOffer]:
        return list(self.get_dependency_offers(self.requirement, ctx=ctx))
