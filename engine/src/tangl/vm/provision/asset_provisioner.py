from __future__ import annotations

"""Provisioner that fulfills explicit asset token requests."""

from typing import Generator, TYPE_CHECKING

from .offer import DependencyOffer, ProvisionCost
from .provisioner import Provisioner
from .requirement import ProvisioningPolicy

if TYPE_CHECKING:  # pragma: no cover - import guarded for typing only
    from tangl.vm.context import Context
    from .requirement import Requirement


class AssetProvisioner(Provisioner):
    """Create tokens from :class:`~tangl.story.fabula.AssetManager` assets.

    Asset provisioning is *opt-in only*: this provisioner emits offers **only**
    when ``requirement.asset_ref`` is set and the referenced asset is registered
    with the active world's :class:`~tangl.story.fabula.AssetManager`.

    It deliberately avoids satisfying normal story-driven requirements. If a
    dependency does not specify :attr:`Requirement.asset_ref`, this provisioner
    remains silent so that :class:`TemplateProvisioner` and other story-centric
    provisioners continue to own narrative provisioning.
    """

    layer: str = "asset"

    def get_dependency_offers(
        self,
        requirement: "Requirement",
        *,
        ctx: "Context",
    ) -> Generator[DependencyOffer, None, None]:
        """Yield a provisioning offer when an explicit ``asset_ref`` is present."""

        asset_ref = requirement.asset_ref
        if not asset_ref:
            return

        graph = getattr(ctx, "graph", None)
        world = getattr(graph, "world", None) if graph is not None else None
        asset_manager = getattr(world, "asset_manager", None) if world is not None else None

        if asset_manager is None or not asset_manager.has_asset(asset_ref):
            return

        if not (requirement.policy & (ProvisioningPolicy.CREATE | ProvisioningPolicy.CLONE | ProvisioningPolicy.ANY)):
            return

        def _accept(ctx: "Context"):
            domain_manager = getattr(world, "domain_manager", None) if world is not None else None
            overlay = requirement.template or {}

            return asset_manager.create_token(
                asset_ref=asset_ref,
                graph=ctx.graph,
                domain_manager=domain_manager,
                **overlay,
            )

        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=ProvisioningPolicy.CLONE,
            base_cost=ProvisionCost.HEAVY_INDIRECT,
            cost=float(ProvisionCost.HEAVY_INDIRECT),
            proximity=0.0,
            proximity_detail="asset token",
            accept_func=_accept,
            source_provisioner_id=self.uid,
            source_layer=self.layer,
        )
