from __future__ import annotations

from pathlib import Path
from typing import Iterator, TYPE_CHECKING

from tangl.vm.context import Context
from tangl.vm.provision import DependencyOffer, ProvisionCost, Provisioner, ProvisioningPolicy
from tangl.media.media_data_type import MediaDataType
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from .media_resource_registry import MediaResourceRegistry

if TYPE_CHECKING:  # pragma: no cover - type checking only to avoid import cycles
    from tangl.vm.planning.media_requirement import MediaRequirement


class MediaProvisioner(Provisioner):
    """Discover or create :class:`MediaResourceInventoryTag` entries for media requirements."""

    media_registry: MediaResourceRegistry | None = None

    def __init__(self, media_registry: MediaResourceRegistry | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, "media_registry", media_registry)
        if self.media_registry is None and getattr(self, "registries", None):
            object.__setattr__(self, "media_registry", self.registries[0])

    def _resolve_existing(self, requirement: MediaRequirement) -> MediaRIT | None:
        if self.media_registry is None or requirement.media_path is None:
            return None

        filename = Path(requirement.media_path).name
        for rit in self.media_registry:
            rit_path = getattr(rit, "path", None)
            if rit_path is None:
                continue
            if Path(rit_path).name == filename:
                return rit
        return None

    def _create_rit(self, requirement: MediaRequirement) -> MediaRIT:
        if requirement.media_path is None:
            raise ValueError("MediaRequirement needs media_path")

        media_type = MediaDataType.from_path(Path(requirement.media_path)) or MediaDataType.IMAGE
        rit = MediaRIT(path=requirement.media_path, data_type=media_type)
        if self.media_registry is not None:
            self.media_registry.add(rit)
        return rit

    def get_dependency_offers(
        self,
        requirement: MediaRequirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        from tangl.vm.planning.media_requirement import MediaRequirement

        if not isinstance(requirement, MediaRequirement):
            return iter(())

        if requirement.media_path is None:
            return iter(())

        existing = self._resolve_existing(requirement)
        if existing and (requirement.policy & ProvisioningPolicy.EXISTING):
            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.EXISTING,
                base_cost=ProvisionCost.DIRECT,
                cost=float(ProvisionCost.DIRECT),
                proximity=0.0,
                proximity_detail="media-cache",
                accept_func=lambda _ctx: existing,
                provider_id=existing.uid,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
            )
            return iter(())

        if not (requirement.policy & ProvisioningPolicy.CREATE):
            return iter(())

        rit = self._create_rit(requirement)
        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=ProvisioningPolicy.CREATE,
            base_cost=ProvisionCost.CREATE,
            cost=float(ProvisionCost.CREATE),
            proximity=0.0,
            proximity_detail="media-create",
            accept_func=lambda _ctx: rit,
            source_provisioner_id=self.uid,
            source_layer=self.layer,
        )
