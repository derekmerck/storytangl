"""Provisioner for token factory-backed requirements."""

from __future__ import annotations

from typing import Iterator, TYPE_CHECKING

from tangl.core.factory.token_factory import TokenFactory
from tangl.core.singleton import Singleton

from .offer import DependencyOffer, ProvisionCost
from .provisioner import Provisioner
from .provisioning_policy import ProvisioningPolicy
from .requirement import Requirement

if TYPE_CHECKING:
    from tangl.vm.context import Context


class TokenProvisioner(Provisioner):
    """Create token nodes using a :class:`~tangl.core.factory.token_factory.TokenFactory`."""

    def __init__(
        self,
        token_factory: TokenFactory | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, "token_factory", token_factory)

    def _get_factory(self, ctx: "Context") -> TokenFactory | None:
        if self.token_factory is not None:
            return self.token_factory

        ctx_factory = getattr(ctx, "token_factory", None)
        if ctx_factory is not None:
            return ctx_factory

        graph = getattr(ctx, "graph", None)
        if graph is None:
            return None

        return getattr(graph, "token_factory", None)

    @staticmethod
    def _resolve_token_type(
        requirement: Requirement,
        *,
        factory: TokenFactory,
    ) -> type[Singleton] | None:
        token_type = requirement.token_type
        if isinstance(token_type, type) and issubclass(token_type, Singleton):
            return token_type
        if isinstance(token_type, str):
            return factory.get_type(token_type)

        token_ref = requirement.token_ref
        if isinstance(token_ref, type) and issubclass(token_ref, Singleton):
            return token_ref

        return None

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: "Context",
    ) -> Iterator[DependencyOffer]:
        if not (requirement.policy & ProvisioningPolicy.CREATE_TOKEN):
            return

        factory = self._get_factory(ctx)
        if factory is None:
            return

        token_type = self._resolve_token_type(requirement, factory=factory)
        token_label = requirement.token_label
        if token_type is None or token_label is None:
            return

        base = factory.resolve_base(token_type, label=token_label)
        if base is None:
            return

        def _accept(ctx: "Context"):
            return factory.materialize_token(
                token_type=token_type,
                label=token_label,
                overlay=requirement.overlay,
            )

        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=ProvisioningPolicy.CREATE_TOKEN,
            base_cost=ProvisionCost.CREATE,
            cost=float(ProvisionCost.CREATE),
            proximity=999.0,
            proximity_detail="token",
            accept_func=_accept,
            source_provisioner_id=self.uid,
            source_layer=self.layer,
        )
