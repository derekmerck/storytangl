"""Provisioners generate offers that can satisfy frontier requirements."""

from __future__ import annotations

import logging
import warnings
from copy import deepcopy
from typing import Iterator, TYPE_CHECKING, Callable, Mapping, Any
from uuid import UUID

from pydantic import ConfigDict

from tangl.core import Edge, Entity, Node, Registry
from tangl.core.factory import TemplateFactory, Template

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
    from tangl.ir.core_ir import BaseScriptItem


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
    factory: TemplateFactory | None = None
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

    # How come this is unused?
    # def get_offers(
    #     self,
    #     requirement: Requirement | "Dependency" | None = None,
    #     *,
    #     ctx: Context,
    #     node: Node | None = None,
    # ) -> list[ProvisionOffer]:
    #     """Compatibility shim returning a concrete list of offers."""
    #
    #     if requirement is not None:
    #         req: Requirement
    #         if hasattr(requirement, "requirement"):
    #             dependency = requirement  # type: ignore[assignment]
    #             req = dependency.requirement  # type: ignore[attr-defined]
    #         else:
    #             req = requirement  # type: ignore[assignment]
    #         return list(self.get_dependency_offers(req, ctx=ctx))
    #
    #     if node is None:
    #         cursor_id = getattr(ctx, "cursor_id", None)
    #         if cursor_id is not None:
    #             node = ctx.graph.get(cursor_id)
    #     if node is None:
    #         raise ValueError("node must be provided when collecting affordance offers")
    #     return list(self.get_affordance_offers(node, ctx=ctx))


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
        if requirement.template_ref is not None and not isinstance(requirement.identifier, str):
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
        factory: TemplateFactory | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        object.__setattr__(self, "factory", factory)

    def _get_factory(self, ctx: "Context") -> TemplateFactory | None:
        """Resolve the active template factory."""

        if self.factory is not None:
            return self.factory

        ctx_factory = getattr(ctx, "factory", None)
        if ctx_factory is not None:
            return ctx_factory

        graph = getattr(ctx, "graph", None)
        if graph is None:
            return None

        return getattr(graph, "factory", None)

    def _coerce_template(self, template: Any) -> Template | "BaseScriptItem" | None:
        if template is None:
            return None
        if isinstance(template, Template):
            return template
        from tangl.ir.core_ir import BaseScriptItem
        if isinstance(template, BaseScriptItem):
            return template
        if isinstance(template, Mapping):
            if "scope" in template:
                return BaseScriptItem.model_validate(dict(template))
            return Template.model_validate(dict(template))
        return None

    def _resolve_template(
        self,
        requirement: Requirement,
        *,
        ctx: "Context",
    ) -> tuple[Template | "BaseScriptItem" | None, dict[str, Any]]:
        provenance: dict[str, Any] = {}
        if requirement.template is not None:
            template = self._coerce_template(requirement.template)
            if template is None:
                return None, provenance
            provenance.update(self._template_provenance(template))
            return template, provenance

        graph = getattr(ctx, "graph", None)
        world = getattr(graph, "world", None) if graph is not None else None
        script_manager = getattr(world, "script_manager", None)

        if script_manager is not None and (requirement.template_ref or requirement.identifier):
            identifier = requirement.template_ref or requirement.identifier
            cursor = getattr(ctx, "cursor", None)
            if cursor is None and graph is not None:
                cursor_id = getattr(ctx, "cursor_id", None)
                if cursor_id is not None:
                    cursor = graph.get(cursor_id)
            criteria = requirement.criteria or {}
            template = script_manager.find_template(
                identifier=str(identifier),
                selector=cursor,
                **criteria,
            )
            if template is not None:
                provenance.update(self._template_provenance(template))
                return template, provenance

        factory = self._get_factory(ctx)
        if factory is None:
            return None, provenance

        cursor = getattr(ctx, "cursor", None)
        if cursor is None:
            graph = getattr(ctx, "graph", None)
            cursor_id = getattr(ctx, "cursor_id", None)
            if graph is not None and cursor_id is not None:
                cursor = graph.get(cursor_id)

        criteria: dict[str, Any] = dict(requirement.criteria or {})
        if cursor is not None:
            criteria.setdefault("selector", cursor)

        template = None
        if requirement.template_ref:
            template, ref_provenance = self._find_template(
                factory,
                requirement.template_ref,
                criteria,
                context=ctx,
            )
            provenance.update(ref_provenance)
            if template is not None:
                provenance["source"] = "template_ref"
        if template is None and requirement.identifier:
            template, id_provenance = self._find_template(
                factory,
                requirement.identifier,
                criteria,
                context=ctx,
            )
            provenance.update(id_provenance)
            if template is not None:
                provenance["source"] = "identifier"
        if template is None and requirement.criteria:
            template = factory.find_one(**criteria)
            if template is not None:
                provenance["source"] = "criteria"
                provenance["lookup_method"] = "criteria_only"

        if template is None:
            return None, provenance

        provenance.update(self._template_provenance(template))
        return template, provenance

    # @staticmethod
    # def _matches_scope(template_data: Mapping[str, Any] | Any, *, ctx: "Context") -> bool:
    #     cursor = getattr(ctx, "cursor", None)
    #     if cursor is None:
    #         graph = getattr(ctx, "graph", None)
    #         cursor_id = getattr(ctx, "cursor_id", None)
    #         if graph is not None and cursor_id is not None:
    #             cursor = graph.get(cursor_id)
    #     criteria: dict[str, Any]
    #     if hasattr(template_data, "get_selection_criteria"):
    #         criteria = template_data.get_selection_criteria() or {}
    #     elif isinstance(template_data, Mapping):
    #         criteria = {}
    #         path_pattern = template_data.get("path_pattern")
    #         if path_pattern:
    #             criteria["has_path"] = path_pattern
    #         ancestor_tags = template_data.get("ancestor_tags")
    #         if ancestor_tags:
    #             criteria["has_ancestor_tags"] = set(ancestor_tags)
    #         forbid_ancestor_tags = template_data.get("forbid_ancestor_tags")
    #         if forbid_ancestor_tags:
    #             criteria["has_ancestor_tags__not"] = set(forbid_ancestor_tags)
    #     else:
    #         criteria = {}
    #
    #     if not criteria:
    #         return True
    #
    #     if cursor is None:
    #         has_path = criteria.get("has_path")
    #         requires_path = has_path not in (None, "*")
    #         requires_tags = bool(
    #             criteria.get("has_ancestor_tags") or criteria.get("has_ancestor_tags__not")
    #         )
    #         return not (requires_path or requires_tags)
    #
    #     has_path = criteria.get("has_path")
    #     if has_path and not cursor.has_path(has_path):
    #         return False
    #     ancestor_tags = criteria.get("has_ancestor_tags")
    #     if ancestor_tags and not cursor.has_ancestor_tags(ancestor_tags):
    #         return False
    #     forbid_ancestor_tags = criteria.get("has_ancestor_tags__not")
    #     if forbid_ancestor_tags and not cursor.has_ancestor_tags__not(forbid_ancestor_tags):
    #         return False
    #     return True

    @staticmethod
    def _find_template(
        factory: TemplateFactory,
        identifier: Any,
        criteria: dict[str, Any],
        *,
        context: Context | None = None,
    ) -> tuple[Template | None, dict[str, Any]]:
        provenance: dict[str, Any] = {}
        if identifier is None:
            return None, provenance
        if not isinstance(identifier, str):
            template = factory.find_one(uid=identifier, **criteria)
            if template is not None:
                provenance["lookup_method"] = "uuid"
            return template, provenance
        if "." not in identifier:
            template = factory.find_one(label=identifier, **criteria)
            if template is not None:
                provenance["lookup_method"] = "label"
            return template, provenance

        template = factory.find_one(path=identifier, **criteria)
        if template is not None:
            provenance["lookup_method"] = "strict_path"
            return template, provenance

        if context is None:
            provenance["lookup_method"] = "path_failed_no_context"
            return None, provenance

        template = _resolve_as_location(
            factory,
            identifier,
            criteria,
            context,
            provenance,
        )

        return template, provenance

    def _get_all_template_offers(
        self,
        identifier: str,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        """Generate offers for all templates matching an identifier."""

        from tangl.story.fabula.address_resolver import iter_matching_templates

        factory = self._get_factory(ctx)
        if factory is None:
            return

        cursor = getattr(ctx, "cursor", None)
        if cursor is None:
            cursor_id = getattr(ctx, "cursor_id", None)
            graph = getattr(ctx, "graph", None)
            if cursor_id and graph:
                cursor = graph.get(cursor_id)

        allow_scope_matches = cursor is not None
        for template, score, is_exact in iter_matching_templates(
            factory,
            identifier,
            selector=cursor,
            allow_archetypes=False,
        ):
            if not allow_scope_matches and not is_exact:
                continue
            if not is_exact and _is_global_only_template(template):
                logger.debug(
                    "Rejecting global-only template '%s' for qualified identifier '%s'",
                    template.label,
                    identifier,
                )
                continue
            def create_node(context: Context, captured: Template = template) -> Node:
                return self._materialize_template(captured, ctx=context, factory=factory)

            provenance = self._template_provenance(template)
            provenance["match_score"] = score
            provenance["is_exact_match"] = is_exact

            base_cost = float(ProvisionCost.CREATE)
            score_penalty = score if isinstance(score, (int, float)) and score > 0 else 0.0
            cost = base_cost + score_penalty

            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.CREATE_TEMPLATE,
                base_cost=ProvisionCost.CREATE,
                cost=cost,
                proximity=999.0,
                proximity_detail="new instance",
                accept_func=create_node,
                source_provisioner_id=self.uid,
                source_layer=self.layer,
                template_ref=provenance.get("template_ref"),
                template_hash=provenance.get("template_hash"),
                template_content_id=provenance.get("template_content_id"),
            )

    @staticmethod
    def _template_payload(
        template: Template | "BaseScriptItem" | Mapping[str, Any],
    ) -> dict[str, Any]:
        if isinstance(template, Template):
            payload = template.unstructure_for_materialize()
        elif hasattr(template, "model_dump"):
            payload = template.model_dump(exclude_none=True)
        else:
            payload = dict(template)
        for key in ("graph", "uid", "content_hash", "seq", "is_dirty_", "obj_cls"):
            payload.pop(key, None)
        tags = payload.get("tags")
        if isinstance(tags, list):
            payload["tags"] = set(tags)
        return payload

    @staticmethod
    def _template_provenance(template: Template | "BaseScriptItem") -> dict[str, Any]:
        if not isinstance(template, Template):
            template_ref = getattr(template, "label", None)
            content_hash = getattr(template, "content_hash", None)
            content_id = getattr(template, "content_identifier", lambda: None)()
            return {
                "template_ref": template_ref,
                "template_hash": content_hash,
                "template_content_id": content_id,
            }
        return {
            "template_ref": template.label,
            "template_hash": template.content_hash,
            "template_content_id": template.content_identifier(),
        }

    @staticmethod
    def _materialize_template(
        template: Template | "BaseScriptItem",
        *,
        ctx: "Context",
        factory: TemplateFactory | None,
    ) -> Node:
        from tangl.core.factory import TemplateFactory
        from tangl.story.fabula.address_resolver import ensure_instance

        graph = getattr(ctx, "graph", None)
        if graph is None:
            raise ValueError("Context must include a graph for materialization.")

        world = getattr(graph, "world", None)
        domain_manager = getattr(world, "domain_manager", None) if world is not None else None
        cursor = getattr(ctx, "cursor", None)
        if cursor is None:
            cursor_id = getattr(ctx, "cursor_id", None)
            if cursor_id is not None:
                cursor = graph.get(cursor_id)

        target_address = getattr(ctx, "target_address", None)
        if not target_address and getattr(template, "declares_instance", False):
            target_address = getattr(template, "path", None)
        if not target_address and cursor is not None:
            parent_path = cursor.path.rsplit(".", 1)[0] if "." in cursor.path else ""
            label = getattr(template, "label", "node")
            target_address = f"{parent_path}.{label}" if parent_path else label
        if not target_address:
            target_address = getattr(template, "label", "node")

        factory = factory or getattr(graph, "factory", None)
        if factory is None:
            factory = TemplateFactory(label="provisioner_factory")
        if template is not None:
            factory.add(template)
        if hasattr(graph, "factory") and getattr(graph, "factory", None) is None:
            setattr(graph, "factory", factory)

        return ensure_instance(
            graph,
            target_address,
            factory,
            anchor=cursor,
            domain_manager=domain_manager,
            world=world,
            allow_archetypes=True,
        )

    def get_dependency_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context,
    ) -> Iterator[DependencyOffer]:
        if not (requirement.policy & ProvisioningPolicy.CREATE_TEMPLATE):
            return
        identifier = requirement.template_ref or requirement.identifier
        if isinstance(identifier, str) and "." in identifier:
            yield from self._get_all_template_offers(identifier, requirement, ctx=ctx)
            return
        template, provenance = self._resolve_template(requirement, ctx=ctx)
        if template is None:
            return

        factory = self._get_factory(ctx)

        def create_node(ctx: Context) -> Node:
            return self._materialize_template(template, ctx=ctx, factory=factory)

        operation = ProvisioningPolicy.CREATE_TEMPLATE
        yield DependencyOffer(
            requirement_id=requirement.uid,
            requirement=requirement,
            operation=operation,
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


def _resolve_as_location(
    factory: TemplateFactory,
    identifier: str,
    criteria: dict[str, Any],
    context: Context,
    provenance: dict[str, Any],
) -> Template | None:
    """Stage 2: try to resolve qualified identifiers as a location."""

    from tangl.story.fabula.address_resolver import iter_matching_templates

    cursor = getattr(context, "cursor", None)
    if cursor is None:
        cursor_id = getattr(context, "cursor_id", None)
        graph = getattr(context, "graph", None)
        if cursor_id and graph:
            cursor = graph.get(cursor_id)

    try:
        matches = list(
            iter_matching_templates(
                factory,
                identifier,
                selector=cursor,
                allow_archetypes=False,
            )
        )
        if criteria:
            matches = [
                (template, score, is_exact)
                for template, score, is_exact in matches
                if template.matches(**criteria)
            ]

        if not matches:
            provenance["lookup_method"] = "location_no_matches"
            return None

        matches.sort(key=lambda item: item[1])
        template, score, is_exact = matches[0]

        if _is_global_only_template(template):
            logger.debug(
                "Rejecting global-only template '%s' for qualified identifier '%s'",
                template.label,
                identifier,
            )
            provenance["lookup_method"] = "location_global_guard"
            provenance["location_guard_triggered"] = True
            return None

        provenance["lookup_method"] = "location_based"
        provenance["location_score"] = score
        provenance["location_is_exact"] = is_exact
        return template
    except Exception as exc:
        logger.debug(
            "Location-based lookup failed for '%s': %s",
            identifier,
            exc,
        )
        provenance["lookup_method"] = "location_exception"
        provenance["location_error"] = str(exc)
        return None


def _is_global_only_template(template: Template) -> bool:
    """Return True when a template is global-only (path_pattern='*')."""

    if hasattr(template, "get_path_pattern"):
        pattern = template.get_path_pattern()
    else:
        pattern = getattr(template, "path_pattern", None)

    return pattern == "*"


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
        if requirement.identifier is None and not requirement.criteria:
            return
        template, _ = self._resolve_template(requirement, ctx=ctx)
        if template is None:
            return

        template_payload = self._template_payload(template)
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
                accept_func=make_update_func(node, deepcopy(template_payload)),
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

        template_payload = self._template_payload(template)
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
            accept_func=make_clone_func(reference, deepcopy(template_payload)),
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
