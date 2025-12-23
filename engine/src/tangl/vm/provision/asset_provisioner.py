from __future__ import annotations

"""Provisioner that fulfills explicit asset token requests."""

from typing import Generator, TYPE_CHECKING

from .offer import DependencyOffer, ProvisionCost
from .provisioner import Provisioner
from .provisioning_policy import ProvisioningPolicy

if TYPE_CHECKING:  # pragma: no cover - import guarded for typing only
    from tangl.vm.context import Context
    from .requirement import Requirement


class AssetProvisioner(Provisioner):
    """Create tokens from :class:`~tangl.story.fabula.AssetManager` assets.

    Asset provisioning is *opt-in only*: this provisioner emits offers **only**
    when ``requirement.token_ref`` is set and the referenced asset is registered
    with the active world's :class:`~tangl.story.fabula.AssetManager`.

    It deliberately avoids satisfying normal story-driven requirements. If a
    dependency does not specify :attr:`Requirement.token_ref`, this provisioner
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
        """Yield a provisioning offer when an explicit ``token_ref`` is present."""

        token_type = requirement.token_type or requirement.token_ref
        token_label = requirement.token_label
        if not token_type or not token_label:
            return

        graph = getattr(ctx, "graph", None)
        world = getattr(graph, "world", None) if graph is not None else None
        asset_manager = getattr(world, "asset_manager", None) if world is not None else None

        if asset_manager is None:
            return
        if not asset_manager.has_token_base(token_type, token_label):
            return

        if not (
            requirement.policy
            & (
                ProvisioningPolicy.CREATE_TEMPLATE
                | ProvisioningPolicy.CREATE_TOKEN
                | ProvisioningPolicy.CLONE
                | ProvisioningPolicy.ANY
            )
        ):
            return

        def _accept(ctx: "Context"):
            overlay = requirement.overlay or requirement.template or {}
            if hasattr(overlay, "model_dump"):
                overlay = overlay.model_dump()
            elif not isinstance(overlay, dict):
                overlay = dict(overlay)

            return asset_manager.create_token(
                token_type=token_type,
                label=token_label,
                graph=ctx.graph,
                overlay=overlay,
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
