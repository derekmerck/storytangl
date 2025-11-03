"""Provisioners generate offers that can satisfy frontier requirements."""

from __future__ import annotations

from copy import deepcopy
from typing import Iterator, TYPE_CHECKING
from uuid import UUID

from pydantic import ConfigDict

from tangl.core import Edge, Entity, Node, Registry

from .offer import (
    AffordanceOffer,
    DependencyOffer,
    ProvisionCost,
    ProvisionOffer,
)
from .requirement import Requirement, ProvisioningPolicy

if TYPE_CHECKING:
    from tangl.vm.context import Context
    from .open_edge import Dependency


class Provisioner(Entity):
    """Base class for objects that propose ways to satisfy requirements."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    node_registry: Registry[Node] | None = None
    template_registry: dict[str, dict] | None = None
    layer: str = "global"

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        raise NotImplementedError

    def get_affordance_offers(
        self,
        node: Node,
        *,
        ctx: Context,
    ) -> Iterator[AffordanceOffer]:
        return iter(())

    def get_offers(
        self,
        requirement: Requirement | "Dependency" | None = None,
        *,
        ctx: Context,
        node: Node | None = None,
    ) -> list[ProvisionOffer]:
        """Compatibility shim returning a concrete list of offers."""

        if requirement is not None:
            req: Requirement
            if hasattr(requirement, "requirement"):
                dependency = requirement  # type: ignore[assignment]
                req = dependency.requirement  # type: ignore[attr-defined]
            else:
                req = requirement  # type: ignore[assignment]
            return list(self.get_dependency_offers(req, ctx=ctx))

        if node is None:
            cursor_id = getattr(ctx, "cursor_id", None)
            if cursor_id is not None:
                node = ctx.graph.get(cursor_id)
        if node is None:
            raise ValueError("node must be provided when collecting affordance offers")
        return list(self.get_affordance_offers(node, ctx=ctx))


class GraphProvisioner(Provisioner):
    """Offer existing nodes from a registry."""

    def __init__(self, node_registry: Registry[Node], **kwargs):
        super().__init__(**kwargs)
        self.node_registry = node_registry

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        if self.node_registry is None:
            return

        seen: set[UUID] = set()
        criteria = requirement.get_selection_criteria()
        for node in self.node_registry.find_all(**criteria):
            if not requirement.satisfied_by(node):
                continue
            if node.uid in seen:
                continue
            seen.add(node.uid)
            yield DependencyOffer(
                requirement_id=requirement.uid,
                operation="EXISTING",
                cost=ProvisionCost.DIRECT,
                provider_id=node.uid,
                accept_func=lambda ctx, n=node: n,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
            )


class TemplateProvisioner(Provisioner):
    """Create new nodes from requirement templates."""

    def __init__(self, template_registry: dict[str, dict] | None = None, **kwargs):
        super().__init__(template_registry=template_registry or {}, **kwargs)

    def _resolve_template(self, requirement: Requirement) -> dict | None:
        if requirement.template is not None:
            return deepcopy(requirement.template)
        if self.template_registry and requirement.identifier:
            template = self.template_registry.get(str(requirement.identifier))
            if template is not None:
                return deepcopy(template)
        return None

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        template = self._resolve_template(requirement)
        if template is None:
            return

        def create_node(ctx: Context) -> Node:
            template_data = deepcopy(template)
            template_data.setdefault("obj_cls", Node)
            template_data["graph"] = ctx.graph
            return Node.structure(template_data)

        yield DependencyOffer(
            requirement_id=requirement.uid,
            operation="CREATE",
            cost=ProvisionCost.CREATE,
            accept_func=create_node,
            source_provisioner_id=self.uid,
            source_layer=self.layer,
        )


class UpdatingProvisioner(TemplateProvisioner):
    """Modify existing nodes with template data."""

    def __init__(self, node_registry: Registry[Node], **kwargs):
        super().__init__(**kwargs)
        self.node_registry = node_registry

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        if self.node_registry is None:
            return
        template = self._resolve_template(requirement)
        if template is None:
            return

        template.pop("graph", None)
        seen: set[UUID] = set()
        criteria = requirement.get_selection_criteria()

        for node in self.node_registry.find_all(**criteria):
            if not requirement.satisfied_by(node):
                continue
            if node.uid in seen:
                continue
            seen.add(node.uid)

            def update_node(ctx: Context, n=node) -> Node:
                n.update_attrs(**template)
                return n

            yield DependencyOffer(
                requirement_id=requirement.uid,
                operation="UPDATE",
                cost=ProvisionCost.LIGHT_INDIRECT,
                accept_func=update_node,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
            )


class CloningProvisioner(TemplateProvisioner):
    """Clone and evolve existing nodes using a template."""

    def __init__(self, node_registry: Registry[Node], **kwargs):
        super().__init__(**kwargs)
        self.node_registry = node_registry

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        if self.node_registry is None:
            return
        template = self._resolve_template(requirement)
        if template is None:
            return

        template.pop("graph", None)
        seen: set[UUID] = set()
        criteria = requirement.get_selection_criteria()

        for node in self.node_registry.find_all(**criteria):
            if not requirement.satisfied_by(node):
                continue
            if node.uid in seen:
                continue
            seen.add(node.uid)

            def clone_node(ctx: Context, n=node) -> Node:
                return n.evolve(**template)

            yield DependencyOffer(
                requirement_id=requirement.uid,
                operation="CLONE",
                cost=ProvisionCost.HEAVY_INDIRECT,
                accept_func=clone_node,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
            )


class CompanionProvisioner(Provisioner):
    """Example provisioner that offers character affordances."""

    companion_node: Node

    def __init__(self, companion_node: Node, **kwargs):
        super().__init__(companion_node=companion_node, **kwargs)

    def get_affordance_offers(
        self,
        node: Node,
        *,
        ctx: Context,
    ) -> Iterator[AffordanceOffer]:
        def create_affordance(label: str, *, target_tags: set[str] | None = None) -> AffordanceOffer:
            def _accept(context: Context, dest: Node) -> Edge:
                from tangl.vm.provision import Affordance

                req = Requirement(
                    graph=context.graph,
                    identifier=self.companion_node.uid,
                    policy=ProvisioningPolicy.EXISTING,
                )
                req.provider = self.companion_node
                return Affordance(
                    graph=context.graph,
                    source=self.companion_node,
                    destination=dest,
                    requirement=req,
                    label=label,
                )

            return AffordanceOffer(
                label=label,
                cost=ProvisionCost.DIRECT,
                accept_func=_accept,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
                target_tags=target_tags or set(),
            )

        yield create_affordance("talk")

        if "happy" in self.companion_node.tags:
            yield create_affordance("sing", target_tags={"musical", "peaceful"})

