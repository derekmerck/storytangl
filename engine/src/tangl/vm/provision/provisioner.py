"""Provisioners generate offers that can satisfy frontier requirements."""

from __future__ import annotations

import logging
from importlib import import_module
from copy import deepcopy
from typing import Iterator, TYPE_CHECKING, Callable, Mapping, Any
from uuid import UUID

from pydantic import ConfigDict

from tangl.core import Edge, Entity, Node, Registry

logger = logging.getLogger(__name__)

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
        if requirement.template_ref is not None:
            return
        if self.node_registry is None:
            return

        seen: set[UUID] = set()
        criteria = requirement.get_selection_criteria() or {}
        for node in self.node_registry.find_all(**criteria):
            if not requirement.satisfied_by(node):
                continue
            if node.uid in seen:
                continue
            seen.add(node.uid)

            proximity, detail = self._calculate_proximity(node, ctx=ctx)
            base_cost = ProvisionCost.DIRECT
            final_cost = float(base_cost) + proximity

            def make_accept_func(captured: Node) -> Callable[["Context"], Node]:
                return lambda ctx: captured

            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.EXISTING,
                base_cost=base_cost,
                cost=final_cost,
                proximity=proximity,
                proximity_detail=detail,
                accept_func=make_accept_func(node),
                provider_id=node.uid,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
            )

    def _calculate_proximity(self, node: Node, *, ctx: Context) -> tuple[float, str]:
        """Return (modifier, description) relative to the active requirement source."""

        source_id = getattr(ctx, "current_requirement_source_id", None)
        if source_id is None:
            source_id = getattr(ctx, "cursor_id", None)
        if source_id is None:
            return 20.0, "unknown"

        source = ctx.graph.get(source_id)
        if source is None:
            return 20.0, "unknown"

        if node.uid == source.uid:
            return 0.0, "same block"

        source_parent = getattr(source, "parent", None)
        node_parent = getattr(node, "parent", None)
        if (
            source_parent is not None
            and node_parent is not None
            and source_parent.uid == node_parent.uid
        ):
            return 5.0, "same scene"

        source_root = getattr(source, "root", None)
        node_root = getattr(node, "root", None)
        if (
            source_root is not None
            and node_root is not None
            and source_root.uid == node_root.uid
        ):
            return 10.0, "same episode"

        return 20.0, "distant"


class TemplateProvisioner(Provisioner):
    """Create new nodes from requirement templates."""

    def __init__(
        self,
        template_registry: Mapping[str, dict] | Registry | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        object.__setattr__(self, "template_registry", template_registry)

    def _get_registry(self, ctx: "Context") -> Mapping[str, dict] | Registry | None:
        """Resolve the template registry from local or world context."""

        if self.template_registry is not None:
            return self.template_registry

        manager = self._get_script_manager(ctx)
        if manager is not None:
            return getattr(manager, "template_registry", None)

        graph = getattr(ctx, "graph", None)
        if graph is None:
            return None

        world = getattr(graph, "world", None)
        if world is None:
            return None

        return getattr(world, "template_registry", None)

    @staticmethod
    def _get_script_manager(ctx: "Context"):
        graph = getattr(ctx, "graph", None)
        if graph is None:
            return None
        world = getattr(graph, "world", None)
        if world is None:
            return None
        if hasattr(world, "__dict__") and "script_manager" in world.__dict__:
            return world.__dict__.get("script_manager")
        return None

    def _normalize_template_payload(self, template: Any) -> dict | None:
        if template is None:
            return None
        if hasattr(template, "model_dump"):
            payload = template.model_dump()
        elif isinstance(template, dict):
            payload = deepcopy(template)
        else:
            try:
                payload = deepcopy(dict(template))
            except TypeError:  # pragma: no cover - defensive fallback
                return None

        obj_cls = payload.get("obj_cls")
        resolved = self._resolve_obj_cls(obj_cls)
        if resolved is not None:
            payload["obj_cls"] = resolved
        elif "obj_cls" in payload and obj_cls is not None:
            payload.pop("obj_cls")

        return payload

    def _resolve_obj_cls(self, obj_cls: Any) -> type | None:
        if isinstance(obj_cls, type):
            return obj_cls
        if isinstance(obj_cls, str):
            try:
                module_path, class_name = obj_cls.rsplit(".", 1)
            except ValueError:
                return Entity.dereference_cls_name(obj_cls)
            try:
                module = import_module(module_path)
            except ImportError:  # pragma: no cover - best-effort fallback
                return Entity.dereference_cls_name(class_name)
            return getattr(module, class_name, None)
        return None

    def _resolve_template(self, requirement: Requirement, *, ctx: "Context") -> tuple[dict | None, dict[str, Any]]:
        provenance: dict[str, Any] = {}
        if requirement.template is not None:
            normalized = self._normalize_template_payload(requirement.template)
            provenance["template_ref"] = getattr(requirement.template, "label", None)
            provenance["template_hash"] = getattr(requirement.template, "content_hash", None)
            provenance["template_content_id"] = self._get_content_identifier(requirement.template)
            return normalized or None, provenance

        manager = self._get_script_manager(ctx)
        registry = None if manager is not None else self._get_registry(ctx)
        if manager is None and registry is None:
            return None, provenance

        cursor = getattr(ctx, "cursor", None)
        if cursor is None:
            graph = getattr(ctx, "graph", None)
            cursor_id = getattr(ctx, "cursor_id", None)
            if graph is not None and cursor_id is not None:
                cursor = graph.get(cursor_id)

        def _scope_from_identifier(identifier: str | None):
            if not identifier or "." not in identifier:
                return None

            try:
                parent_label, _ = identifier.rsplit(".", 1)
            except ValueError:  # pragma: no cover - defensive
                return None

            from tangl.ir.story_ir.story_script_models import ScopeSelector

            return ScopeSelector(parent_label=parent_label)

        def _find_template(**criteria: Any) -> Any:
            if isinstance(registry, Mapping):
                identifier = criteria.get("has_identifier")
                label = criteria.get("label")

                if identifier is not None and isinstance(identifier, str):
                    if identifier in registry:
                        return registry.get(identifier)

                    if "." in identifier:
                        _, tail = identifier.rsplit(".", 1)
                        if tail in registry:
                            return registry.get(tail)

                if label is not None:
                    return registry.get(label)

                return None

            find_one = getattr(registry, "find_one", None)
            if callable(find_one):
                return find_one(**criteria)

            return None

        def _build_search(identifier: str | None) -> dict[str, Any]:
            scope_hint = _scope_from_identifier(identifier) or _scope_from_identifier(
                requirement.identifier
            )

            search: dict[str, Any] = {"selector": cursor}
            if identifier is None:
                return search

            search["has_identifier"] = identifier

            if "." not in identifier and scope_hint is not None:
                search.setdefault("has_scope", scope_hint)

            return search

        criteria = requirement.criteria or {}
        template: Any | None = None

        if manager is not None:
            if requirement.template_ref:
                template = manager.find_template(
                    identifier=requirement.template_ref,
                    selector=cursor,
                    **criteria,
                )
            if template is None and requirement.identifier:
                template = manager.find_template(
                    identifier=requirement.identifier,
                    selector=cursor,
                    **criteria,
                )
            if template is None and criteria:
                template = manager.find_template(selector=cursor, **criteria)

        if manager is None:
            if requirement.template_ref:
                template = _find_template(**_build_search(requirement.template_ref))

            if template is None and requirement.identifier:
                template = _find_template(**_build_search(requirement.identifier))

            if template is None and criteria:
                template = _find_template(selector=cursor, **criteria)

        if template is not None:
            provenance["template_ref"] = getattr(template, "label", None)
            provenance["template_hash"] = getattr(template, "content_hash", None)
            provenance["template_content_id"] = self._get_content_identifier(template)

        normalized = self._normalize_template_payload(template)
        return normalized or None, provenance

    @staticmethod
    def _get_content_identifier(template: Any) -> str | None:
        identifier = getattr(template, "content_identifier", None)
        if identifier is None:
            return None
        if callable(identifier):
            try:
                return identifier()
            except TypeError:  # pragma: no cover - defensive guard
                return None
        return str(identifier)

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        if not (requirement.policy & ProvisioningPolicy.CREATE):
            return
        template, provenance = self._resolve_template(requirement, ctx=ctx)
        if template is None:
            return

        def create_node(ctx: Context) -> Node:
            if isinstance(template, dict):
                from tangl.ir.core_ir import BaseScriptItem

                normalized = dict(template)
                obj_cls_value = normalized.get("obj_cls")
                if isinstance(obj_cls_value, type):
                    module = getattr(obj_cls_value, "__module__", "")
                    qualname = getattr(obj_cls_value, "__qualname__", obj_cls_value.__name__)
                    normalized["obj_cls"] = f"{module}.{qualname}" if module else qualname

                template_model = BaseScriptItem.model_validate(normalized)
            elif hasattr(template, "model_dump"):
                template_model = template
            else:
                raise TypeError(
                    f"Template must be dict or Pydantic model, got {type(template)}"
                )

            world = getattr(ctx.graph, "world", None)
            world_materialize = getattr(world, "_materialize_from_template", None) if world else None

            parent_container = None
            scope_selector = getattr(template_model, "scope", None)
            if scope_selector:
                if world is not None and hasattr(world, "ensure_scope"):
                    parent_container = world.ensure_scope(scope_selector, ctx.graph)
                elif scope_selector.parent_label:
                    find_subgraph = getattr(ctx.graph, "find_subgraph", None)
                    if callable(find_subgraph):
                        parent_container = find_subgraph(label=scope_selector.parent_label)
                    else:
                        parent_container = ctx.graph.get(scope_selector.parent_label)
                    if parent_container is None:
                        raise ValueError(
                            f"Template '{template_model.label}' requires parent scene "
                            f"'{scope_selector.parent_label}' which doesn't exist."
                        )

            if world is None or not callable(world_materialize):
                payload = template_model.model_dump()
                obj_cls_value = payload.get("obj_cls")
                resolved_cls = self._resolve_obj_cls(obj_cls_value)

                resolved_cls = resolved_cls or Node
                payload["obj_cls"] = resolved_cls
                payload.setdefault("graph", ctx.graph)

                try:
                    node = resolved_cls.structure(payload)  # type: ignore[arg-type]
                except AttributeError:  # pragma: no cover - extremely defensive
                    node = Entity.structure(payload)

                if hasattr(ctx.graph, "add") and node not in ctx.graph:
                    ctx.graph.add(node)
                if parent_container is not None and hasattr(parent_container, "add_member"):
                    parent_container.add_member(node)
                return node

            return world_materialize(
                template=template_model,
                graph=ctx.graph,
                parent_container=parent_container,
            )

        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=ProvisioningPolicy.CREATE,
            base_cost=ProvisionCost.CREATE,
            cost=float(ProvisionCost.CREATE),
            proximity=999.0,
            proximity_detail="new instance",
            accept_func=create_node,
            source_provisioner_id=self.uid,
            source_layer=self.layer,
            template_ref=provenance.get("template_ref"),
            template_hash=provenance.get("template_hash"),
            template_content_id=provenance.get("template_content_id"),
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
        template, _ = self._resolve_template(requirement, ctx=ctx)
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
                base_cost=ProvisionCost.LIGHT_INDIRECT,
                cost=float(ProvisionCost.LIGHT_INDIRECT),
                proximity=999.0,
                proximity_detail="update",
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
        template, _ = self._resolve_template(requirement, ctx=ctx)
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
            base_cost=ProvisionCost.HEAVY_INDIRECT,
            cost=float(ProvisionCost.HEAVY_INDIRECT),
            proximity=999.0,
            proximity_detail="clone",
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
                base_cost=ProvisionCost.DIRECT,
                cost=float(ProvisionCost.DIRECT),
                proximity=0.0,
                proximity_detail="affordance",
                accept_func=_accept,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
                target_tags=target_tags or set(),
            )

        yield create_affordance("talk")

        if "happy" in self.companion_node.tags:
            yield create_affordance("sing", target_tags={"musical", "peaceful"})

