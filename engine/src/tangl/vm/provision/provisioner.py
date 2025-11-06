"""Provisioners generate offers that can satisfy frontier requirements."""

from __future__ import annotations

from copy import deepcopy
from typing import Iterator, TYPE_CHECKING, Callable
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


def calculate_provisioner_proximity(
    provisioner: "Provisioner",
    cursor: Node,
) -> int:
    """Stub structural distance helper for planning dispatch.

    The real implementation will walk ancestor chains from ``cursor`` to locate
    ``provisioner.scope_node_id``.  Until planning dispatch is rewritten the
    helper returns a sentinel ``999`` value for scoped and global provisioners
    alike.  Provisioners that set :attr:`Provisioner.scope_node_id` allow
    planning to prefer local offers once this helper is completed.
    """

    if provisioner.scope_node_id is None:
        return 999
    # TODO: Implement ancestor walk to compute actual distance once planning dispatch hooks in.
    return 999


class Provisioner(Entity):
    """Base class for objects that propose ways to satisfy requirements."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    node_registry: Registry[Node] | None = None
    template_registry: dict[str, dict] | None = None
    layer: str = "global"
    scope_node_id: UUID | None = None
    """Identifier of the node or subgraph that owns this provisioner."""

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
        if not (requirement.policy & ProvisioningPolicy.EXISTING):
            return
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

            def make_accept_func(captured: Node) -> Callable[["Context"], Node]:
                return lambda ctx: captured

            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.EXISTING,
                cost=ProvisionCost.DIRECT,
                accept_func=make_accept_func(node),
                provider_id=node.uid,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
            )


class TemplateProvisioner(Provisioner):
    """Create new nodes from requirement templates."""

    def __init__(self, template_registry: dict[str, dict] | None = None, **kwargs):
        super().__init__(template_registry=template_registry or {}, **kwargs)

    def _resolve_template(self, requirement: Requirement) -> dict | None:
        if requirement.template is not None:
            template = deepcopy(requirement.template)
            if not template:
                return None
            return template
        if self.template_registry and requirement.identifier:
            template = self.template_registry.get(str(requirement.identifier))
            if template is not None:
                template_copy = deepcopy(template)
                if not template_copy:
                    return None
                return template_copy
        return None

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        if not (requirement.policy & ProvisioningPolicy.CREATE):
            return
        template = self._resolve_template(requirement)
        if template is None:
            return

        def create_node(ctx: Context) -> Node:
            template_data = deepcopy(template)
            template_data.pop("graph", None)
            template_data.setdefault("obj_cls", Node)
            node = Node.structure(template_data)
            if node not in ctx.graph:
                ctx.graph.add(node)
            return node

        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=ProvisioningPolicy.CREATE,
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
        if not (requirement.policy & ProvisioningPolicy.UPDATE):
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

            def make_update_func(
                captured: Node,
                update_data: dict,
            ) -> Callable[["Context"], Node]:
                def update_node(ctx: Context) -> Node:
                    captured.update_attrs(**update_data)
                    return captured

                return update_node

            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.UPDATE,
                cost=ProvisionCost.LIGHT_INDIRECT,
                accept_func=make_update_func(node, deepcopy(template)),
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
        if not (requirement.policy & ProvisioningPolicy.CLONE):
            return
        if requirement.reference_id is None:
            raise ValueError("CLONE policy requires reference_id to specify source node")
        template = self._resolve_template(requirement)
        if template is None:
            raise ValueError("CLONE policy requires template to evolve clone")
        if self.node_registry is None:
            return

        template.pop("graph", None)
        reference = self.node_registry.get(requirement.reference_id)
        if reference is None:
            return

        def make_clone_func(
            captured: Node,
            evolve_data: dict,
        ) -> Callable[["Context"], Node]:
            def clone_node(ctx: Context) -> Node:
                clone = captured.evolve(**evolve_data)
                if clone not in ctx.graph:
                    ctx.graph.add(clone)
                return clone

            return clone_node

        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=ProvisioningPolicy.CLONE,
            cost=ProvisionCost.HEAVY_INDIRECT,
            accept_func=make_clone_func(reference, deepcopy(template)),
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

