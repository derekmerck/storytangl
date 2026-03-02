from dataclasses import dataclass
from enum import StrEnum
import logging
import warnings
from typing import Any, Iterable, Iterator, Optional, TypeAlias, Union, Self
from uuid import UUID

from tangl.core38 import (
    Edge,
    Entity,
    EntityGroup,
    EntityTemplate,
    Priority,
    RegistryAware,
    TemplateRegistry,
    resolve_ctx,
    Node,
    Selector,
)
from ..dispatch import do_get_token_catalogs, on_provision
from ..ctx import VmResolverCtx
from ..traversable import TraversableNode
from .matching import annotate_offer_specificity, summarize_offer
from .preview import Blocker, ViabilityResult
from .provisioner import (
    ProvisionOffer,
    FindProvisioner,
    TemplateProvisioner,
    TokenProvisioner,
    InlineTemplateProvisioner,
    FallbackProvisioner,
    UpdateCloneProvisioner,
    ProvisionPolicy,
    _next_provision_uid,
    _template_hash_value,
)
from .requirement import Requirement, PT, Dependency, Affordance
from .scope import (
    build_plan,
    prefix_paths,
    resolve_target_path,
    scope_distance,
    split_path,
    target_context_candidates,
)

logger = logging.getLogger(__name__)


class _MaterializeRole(StrEnum):
    INIT = "init"
    PROVISION_INTERMEDIATE = "provision_intermediate"
    PROVISION_LEAF = "provision_leaf"


@dataclass
class Resolver:

    # order of the groups indicates 'distance' from the requirement carrier,
    # so resolver can be created per frontier node and then re-used multiple
    # times to resolve its requirements.
    # Pushes entire 'scope' discussion into however the frontier wants to define
    # it and provides a working default with a single group, single distance.

    location_entity_groups: Iterable[Iterable[Any]] = ()
    template_scope_groups: Iterable[TemplateRegistry] = ()
    # Legacy aliases kept for backward compatibility.
    entity_groups: Iterable[Iterable[Any]] = ()
    template_groups: Iterable[TemplateRegistry] = ()

    def __post_init__(self) -> None:
        if not self.location_entity_groups and self.entity_groups:
            self.location_entity_groups = self.entity_groups
        if not self.template_scope_groups and self.template_groups:
            self.template_scope_groups = self.template_groups

    @staticmethod
    def _ctx_location_entity_groups(ctx) -> Iterable[Iterable[Any]]:
        getter = getattr(ctx, "get_location_entity_groups", None)
        if callable(getter):
            return getter()
        getter = getattr(ctx, "get_entity_groups", None)
        if callable(getter):
            warnings.warn(
                "Resolver context uses legacy get_entity_groups(); "
                "prefer get_location_entity_groups().",
                DeprecationWarning,
                stacklevel=2,
            )
            return getter()
        raise TypeError(
            "Resolver context must provide get_location_entity_groups() or get_entity_groups()"
        )

    @staticmethod
    def _ctx_template_scope_groups(ctx) -> Iterable[TemplateRegistry]:
        getter = getattr(ctx, "get_template_scope_groups", None)
        if callable(getter):
            return getter()
        getter = getattr(ctx, "get_template_groups", None)
        if callable(getter):
            warnings.warn(
                "Resolver context uses legacy get_template_groups(); "
                "prefer get_template_scope_groups().",
                DeprecationWarning,
                stacklevel=2,
            )
            return getter()
        raise TypeError(
            "Resolver context must provide get_template_scope_groups() or get_template_groups()"
        )

    @classmethod
    def from_ctx(cls, ctx: VmResolverCtx) -> Self:
        return cls(
            location_entity_groups=cls._ctx_location_entity_groups(ctx),
            template_scope_groups=cls._ctx_template_scope_groups(ctx),
        )

    @staticmethod
    def _selector_identifier(requirement: Requirement) -> str | None:
        extra = requirement.__pydantic_extra__ or {}
        value = extra.get("has_identifier")
        if isinstance(value, str) and value:
            return value
        return None

    @staticmethod
    def _is_episode_requirement(requirement: Requirement) -> bool:
        extra = requirement.__pydantic_extra__ or {}
        kind = extra.get("has_kind")
        return isinstance(kind, type) and issubclass(kind, TraversableNode)

    @staticmethod
    def _request_ctx_path(_ctx: Any) -> str:
        _ctx = resolve_ctx(_ctx)
        if _ctx is None:
            return ""

        cursor = getattr(_ctx, "cursor", None)
        if cursor is None:
            graph = getattr(_ctx, "graph", None)
            cursor_id = getattr(_ctx, "cursor_id", None)
            if graph is not None and cursor_id is not None and hasattr(graph, "get"):
                cursor = graph.get(cursor_id)

        if cursor is None:
            return ""
        path = getattr(cursor, "path", None)
        if isinstance(path, str) and path:
            return path
        label = getattr(cursor, "label", None)
        if isinstance(label, str):
            return label
        return ""

    @staticmethod
    def _story_materialize_hook(_ctx: Any) -> Any:
        hook = getattr(_ctx, "story_materialize", None)
        if callable(hook):
            return hook

        meta = getattr(_ctx, "meta", None)
        if isinstance(meta, dict):
            meta_hook = meta.get("story_materialize")
            if callable(meta_hook):
                return meta_hook
        return None

    @staticmethod
    def _materialize_node(
        template: EntityTemplate,
        *,
        _ctx: Any = None,
        role: _MaterializeRole | str = _MaterializeRole.PROVISION_LEAF,
        story_materialize: Any = None,
    ) -> Entity:
        if isinstance(role, str):
            role = _MaterializeRole(role)
        if role in (_MaterializeRole.INIT, _MaterializeRole.PROVISION_INTERMEDIATE):
            provider = template.materialize(uid=_next_provision_uid(_ctx=_ctx))
        elif role is _MaterializeRole.PROVISION_LEAF:
            if callable(story_materialize):
                provider = story_materialize(template, _ctx)
            else:
                provider = template.materialize(uid=_next_provision_uid(_ctx=_ctx))
        else:
            raise ValueError(f"Unsupported materialization role: {role!r}")

        if not isinstance(provider, Entity):
            raise TypeError(
                "Template materialization must yield Entity-compatible providers"
            )
        provider.templ_hash = _template_hash_value(template)
        return provider

    @staticmethod
    def _attach_child(parent: Any, child: Any) -> None:
        if parent is None or not hasattr(parent, "add_child"):
            return
        parent.add_child(child)
        finalize = getattr(parent, "finalize_container_contract", None)
        if callable(finalize):
            finalize()

    def _resolve_target_path_for_requirement(self, requirement: Requirement, *, _ctx: Any = None) -> str | None:
        return resolve_target_path(
            identifier=self._selector_identifier(requirement),
            request_ctx=self._request_ctx_path(_ctx),
            authored_path=requirement.authored_path,
            is_qualified=requirement.is_qualified,
            is_absolute=requirement.is_absolute,
        )

    def _template_offers_for_requirement(
        self,
        requirement: Requirement[PT],
        *,
        _ctx: Any = None,
    ) -> list[ProvisionOffer]:
        request_ctx = self._request_ctx_path(_ctx)
        graph = getattr(_ctx, "graph", None)
        story_materialize = self._story_materialize_hook(_ctx)

        provisioner = TemplateProvisioner(
            registries=self.template_scope_groups,
            request_ctx=request_ctx,
            graph=graph,
            story_materialize=story_materialize,
            materialize_node=self._materialize_node,
        )
        return list(provisioner.get_dependency_offers(requirement))

    def _token_offers_for_requirement(
        self,
        requirement: Requirement[PT],
        *,
        _ctx: Any = None,
    ) -> list[ProvisionOffer]:
        _ctx = resolve_ctx(_ctx)
        if _ctx is None:
            return []

        caller = getattr(_ctx, "cursor", None)
        catalogs = do_get_token_catalogs(
            caller,
            requirement=requirement,
            ctx=_ctx,
        )
        if not catalogs:
            return []
        return list(TokenProvisioner(catalogs=catalogs).get_dependency_offers(requirement))

    def inspect_template_dependency_offers(
        self,
        requirement: Requirement[PT],
        *,
        force: bool = False,
        _ctx: Any = None,
    ) -> list[ProvisionOffer]:
        """Return template-only dependency offers using resolver matching semantics."""
        offers = self._template_offers_for_requirement(requirement, _ctx=_ctx)
        offers = [annotate_offer_specificity(requirement, offer) for offer in offers]

        def _allowed(offer: ProvisionOffer) -> bool:
            if offer.policy & ProvisionPolicy.FORCE:
                return force
            return bool(offer.policy & requirement.provision_policy)

        offers = [offer for offer in offers if _allowed(offer)]
        offers.sort(key=lambda v: v.sort_key())
        return offers

    def _iter_templates(self) -> Iterator[EntityTemplate]:
        for registry in self.template_scope_groups:
            if not isinstance(registry, TemplateRegistry):
                continue
            yield from registry.values()

    def gather_offers(
        self,
        requirement: Requirement[PT],
        *,
        force: bool = False,
        preferred_offers: Iterable[ProvisionOffer] = (),
        _ctx=None,
    ) -> list[ProvisionOffer]:
        offers: list[ProvisionOffer] = list(preferred_offers or [])

        # If there are more than 20 groups, the distance-based priorities will slip
        # from the NORMAL tier to LATE, maybe just collapse everything after a few scopes
        # out but not global into "far away" tier and then include globals as the last group.
        for i, entity_group in enumerate(self.location_entity_groups):
            offers.extend(FindProvisioner(values=entity_group, distance=i).get_dependency_offers(requirement))

        offers.extend(self._template_offers_for_requirement(requirement, _ctx=_ctx))
        offers.extend(self._token_offers_for_requirement(requirement, _ctx=_ctx))

        offers.extend(
            InlineTemplateProvisioner(
                materialize_node=self._materialize_node,
                story_materialize=self._story_materialize_hook(_ctx),
            ).iter_dependency_offers(requirement)
        )
        offers.extend(UpdateCloneProvisioner.get_dependency_offers(requirement=requirement, offers=offers))

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # give dispatch a chance to modify the offers
            from tangl.vm38.dispatch import do_resolve
            try:
                resolved_offers = do_resolve(requirement=requirement, offers=offers, ctx=_ctx)
            except TypeError as exc:
                requirement.resolution_reason = "override_invalid"
                requirement.resolution_meta = {"error": str(exc)}
            else:
                if resolved_offers is not None:
                    offers = resolved_offers

        offers = [annotate_offer_specificity(requirement, offer) for offer in offers]

        def _allowed(offer: ProvisionOffer) -> bool:
            if offer.policy & ProvisionPolicy.FORCE:
                return force
            return bool(offer.policy & requirement.provision_policy)

        offers = [offer for offer in offers if _allowed(offer)]

        # Judgment call: synthetic fallback is an emergency path only.
        # It is offered only when force=True and no other provider yielded a valid offer.
        if force and not offers:
            offers.extend(FallbackProvisioner.get_dependency_offers(requirement))

        offers.sort(key=lambda v: v.sort_key())
        return offers

    @staticmethod
    def _iter_local_affordance_providers(frontier: Node | None) -> Iterable[RegistryAware]:
        """Yield unique providers from affordances pushed out of ``frontier``.

        Contract: frontier is affordance ``predecessor`` and provider/resource is
        affordance ``successor``.
        """
        if frontier is None:
            return

        seen_ids: set[UUID] = set()
        if hasattr(frontier, "edges_out"):
            affordances = frontier.edges_out(Selector(has_kind=Affordance))
        else:
            graph = getattr(frontier, "graph", None)
            if graph is None:
                return
            affordances = graph.find_edges(Selector(has_kind=Affordance, predecessor=frontier))

        for affordance in affordances:
            provider = affordance.successor
            if provider is None:
                # Backward compatibility for stale serialized affordances.
                provider = affordance.provider

            if not isinstance(provider, RegistryAware):
                continue
            if provider.uid in seen_ids:
                continue
            seen_ids.add(provider.uid)
            yield provider

    def _linked_affordance_offers(
        self,
        *,
        requirement: Requirement[PT],
        frontier: Node | None,
    ) -> list[ProvisionOffer]:
        """Build EXISTING offers from already-linked local affordance providers."""
        offers: list[ProvisionOffer] = []
        for provider in self._iter_local_affordance_providers(frontier):
            try:
                if not requirement.satisfied_by(provider):
                    continue
            except Exception as exc:
                logger.debug(
                    "requirement.satisfied_by failed for requirement=%s provider=%s",
                    requirement,
                    provider,
                    exc_info=exc,
                )
                continue
            offers.append(
                ProvisionOffer(
                    origin_id="LinkedAffordance",
                    policy=ProvisionPolicy.EXISTING,
                    priority=Priority.EARLY,
                    distance_from_caller=0,
                    candidate=provider,
                    callback=lambda *_, _provider=provider, **__: _provider,
                )
            )
        return offers

    def _resolve_requirement_offer(
        self,
        requirement: Requirement[PT],
        *,
        force: bool = False,
        preferred_offers: Iterable[ProvisionOffer] = (),
        _ctx=None,
    ) -> tuple[Optional[PT], Optional[ProvisionOffer], list[ProvisionOffer]]:
        offers = self.gather_offers(
            requirement,
            force=force,
            preferred_offers=preferred_offers,
            _ctx=_ctx,
        )

        if len(offers) == 0:
            # No valid offers available
            requirement.unsatisfiable = True
            requirement.unambiguously_resolved = None
            requirement.selected_offer_policy = None
            requirement.resolved_step = None
            requirement.resolved_cursor_id = None
            if requirement.resolution_reason is None:
                requirement.resolution_reason = "no_offers"
            requirement.resolution_meta = requirement.resolution_meta or {
                "alternatives": [],
            }
            return None, None, offers
        else:
            requirement.unsatisfiable = False

        requirement.unambiguously_resolved = len(offers) == 1

        for selected_offer in offers:
            requirement.selected_offer_policy = selected_offer.policy
            requirement.resolution_reason = "resolved"
            requirement.resolution_meta = {
                "selected": summarize_offer(selected_offer),
                "alternatives": [summarize_offer(offer) for offer in offers[:5]],
            }

            provider = selected_offer.callback(_ctx=_ctx)
            if provider is not None:
                return provider, selected_offer, offers

        requirement.unsatisfiable = True
        requirement.selected_offer_policy = None
        requirement.resolution_reason = "provider_none"
        return None, None, offers

    def resolve_requirement(
        self,
        requirement: Requirement[PT],
        *,
        force: bool = False,
        preferred_offers: Iterable[ProvisionOffer] = (),
        _ctx=None,
    ) -> Optional[PT]:
        provider, _, _ = self._resolve_requirement_offer(
            requirement=requirement,
            force=force,
            preferred_offers=preferred_offers,
            _ctx=_ctx,
        )
        return provider

    @staticmethod
    def _matches_identifier(candidate: Any, identifier: str) -> bool:
        has_identifier = getattr(candidate, "has_identifier", None)
        if callable(has_identifier):
            try:
                return bool(has_identifier(identifier))
            except (TypeError, ValueError, AttributeError):
                return False
        return getattr(candidate, "label", None) == identifier

    def _find_existing_path_node(self, graph: Any, path: str) -> Any | None:
        segments = split_path(path)
        if not segments:
            return None

        current = None
        for index, segment in enumerate(segments):
            if index == 0:
                current = self._find_top_level_node(graph, segment)
            else:
                current = self._find_child_node(current, segment)
            if current is None:
                return None
        return current

    def _find_top_level_node(self, graph: Any, segment: str) -> Any | None:
        values = getattr(graph, "values", None)
        if not callable(values):
            return None
        for candidate in values():
            if getattr(candidate, "parent", None) is not None:
                continue
            if self._matches_identifier(candidate, segment):
                return candidate
        return None

    def _find_child_node(self, parent: Any, segment: str) -> Any | None:
        if parent is None:
            return None

        children = getattr(parent, "children", None)
        if callable(children):
            for candidate in children():
                if self._matches_identifier(candidate, segment):
                    return candidate
            return None

        members = getattr(parent, "members", None)
        if callable(members):
            for candidate in members():
                if self._matches_identifier(candidate, segment):
                    return candidate
            return None
        return None

    def _find_structural_template(self, *, identifier: str, target_ctx: str) -> EntityTemplate | None:
        best: tuple[int, int, EntityTemplate] | None = None
        for template in self._iter_templates():
            if not template.has_identifier(identifier):
                continue
            if not template.has_payload_kind(TraversableNode):
                continue
            if not template.admitted_to(target_ctx):
                continue
            key = (
                scope_distance(template.admission_scope, target_ctx),
                int(getattr(template, "seq", 0)),
            )
            if best is None or key < (best[0], best[1]):
                best = (key[0], key[1], template)
        if best is None:
            return None
        return best[2]

    def _chain_paths_resolvable(
        self,
        *,
        build_segments: list[str],
        target_ctx: str,
        graph: Any,
    ) -> bool:
        if not build_segments:
            return True
        if graph is None:
            return False

        target_prefix_paths = prefix_paths(target_ctx)[:-1]
        prefix_segments = split_path(target_ctx)[:-1]
        if not prefix_segments:
            return False

        segment_index = 0
        plan_index = 0
        while segment_index < len(prefix_segments) and plan_index < len(build_segments):
            if prefix_segments[segment_index] == build_segments[plan_index]:
                segment_path = target_prefix_paths[segment_index]
                if self._find_existing_path_node(graph, segment_path) is None:
                    template = self._find_structural_template(
                        identifier=segment_path,
                        target_ctx=target_ctx,
                    )
                    if template is None:
                        return False
                plan_index += 1
            segment_index += 1
        return plan_index == len(build_segments)

    def _execute_build_chain(
        self,
        *,
        requirement: Requirement,
        offer: ProvisionOffer,
        graph: Any,
        _ctx: Any = None,
    ) -> Any | None:
        build_segments = list(offer.build_plan or [])
        offer_target_ctx = getattr(offer, "target_ctx", None)
        if not build_segments:
            target_path = offer_target_ctx or self._resolve_target_path_for_requirement(
                requirement,
                _ctx=_ctx,
            )
            if not target_path:
                return None
            parent_path_parts = split_path(target_path)[:-1]
            if not parent_path_parts:
                return None
            return self._find_existing_path_node(graph, ".".join(parent_path_parts))

        target_ctx = offer_target_ctx or self._resolve_target_path_for_requirement(
            requirement,
            _ctx=_ctx,
        )
        if target_ctx is None:
            raise ValueError("Cannot execute structural chain without a target path")

        if not self._chain_paths_resolvable(
            build_segments=build_segments,
            target_ctx=target_ctx,
            graph=graph,
        ):
            raise ValueError("structural build chain is not resolvable")

        segments = split_path(target_ctx)
        parent_segments = segments[:-1]
        if not parent_segments:
            return None

        current: Any | None = None
        for index, segment in enumerate(parent_segments):
            if index == 0:
                existing = self._find_top_level_node(graph, segment)
            else:
                existing = self._find_child_node(current, segment)

            if existing is not None:
                current = existing
                continue

            segment_path = ".".join(segments[: index + 1])
            template = self._find_structural_template(identifier=segment_path, target_ctx=target_ctx)
            if template is None:
                raise ValueError(f"Missing structural template for segment {segment_path!r}")

            created = self._materialize_node(
                template,
                _ctx=_ctx,
                role=_MaterializeRole.PROVISION_INTERMEDIATE,
            )
            if not isinstance(created, RegistryAware):
                raise TypeError("Structural template materialization must yield RegistryAware nodes")

            if created.registry is not graph:
                graph.add(created, _ctx=_ctx)
            self._attach_child(current, created)
            current = created

        return current

    @staticmethod
    def _bind_dependency_provider(
        *,
        dependency: Dependency,
        provider: PT,
        parent: Any | None = None,
        _ctx: Any = None,
    ) -> bool:
        if not isinstance(provider, RegistryAware):
            raise TypeError("Dependency providers must be RegistryAware")

        created = provider.registry is not dependency.registry
        if created:
            dependency.registry.add(provider, _ctx=_ctx)
            if getattr(provider, "parent", None) is not parent:
                Resolver._attach_child(parent, provider)

        dependency.set_provider(provider, _ctx=_ctx)
        return True

    def preview_requirement(
        self,
        requirement: Requirement,
        *,
        force: bool = False,
        preferred_offers: Iterable[ProvisionOffer] = (),
        max_depth: int = 8,
        _ctx: Any = None,
    ) -> ViabilityResult:
        # depth/visited are reserved for future recursive chain variants.
        _ = max_depth
        offers = self.gather_offers(
            requirement,
            force=force,
            preferred_offers=preferred_offers,
            _ctx=_ctx,
        )

        graph = getattr(_ctx, "graph", None)
        for offer in offers:
            chain = list(offer.build_plan or [])
            target_ctx = getattr(offer, "target_ctx", None) or self._resolve_target_path_for_requirement(
                requirement,
                _ctx=_ctx,
            )
            if chain and (
                target_ctx is None
                or not self._chain_paths_resolvable(
                    build_segments=chain,
                    target_ctx=target_ctx,
                    graph=graph,
                )
            ):
                continue
            return ViabilityResult(
                viable=True,
                chain=chain,
                scope_distance=int(getattr(offer, "scope_distance", 0) or 0),
                blockers=[],
            )

        blockers = self._diagnose_blockers(requirement=requirement, _ctx=_ctx)
        return ViabilityResult(viable=False, chain=[], scope_distance=0, blockers=blockers)

    def _diagnose_blockers(self, *, requirement: Requirement, _ctx: Any = None) -> list[Blocker]:
        identifier = self._selector_identifier(requirement)
        request_ctx = self._request_ctx_path(_ctx)
        target_ctxs = target_context_candidates(
            identifier=identifier,
            request_ctx=request_ctx,
            authored_path=requirement.authored_path,
            is_qualified=requirement.is_qualified,
            is_absolute=requirement.is_absolute,
        )
        if not target_ctxs:
            target_ctx = self._resolve_target_path_for_requirement(requirement, _ctx=_ctx)
            if target_ctx is not None:
                target_ctxs = [target_ctx]

        templates = list(self._iter_templates())
        identity_candidates = [
            template
            for template in templates
            if TemplateProvisioner._matches_non_identifier_criteria(requirement, template)
            and TemplateProvisioner._matches_template_identity(requirement, template)
        ]

        if not identity_candidates:
            kind = (requirement.__pydantic_extra__ or {}).get("has_kind")
            if isinstance(kind, type):
                kind_candidates = [template for template in templates if template.has_kind(kind)]
                if kind_candidates:
                    return [
                        Blocker(
                            reason="name_mismatch",
                            context={
                                "identifier": identifier,
                                "target_ctx": target_ctxs[0] if target_ctxs else None,
                            },
                        )
                    ]
            return [
                Blocker(
                    reason="no_template",
                    context={
                        "identifier": identifier,
                        "target_ctx": target_ctxs[0] if target_ctxs else None,
                    },
                )
            ]

        admitted_candidates = [
            (template, target_ctx)
            for template in identity_candidates
            for target_ctx in target_ctxs
            if template.admitted_to(target_ctx)
        ]
        if not admitted_candidates:
            return [
                Blocker(
                    reason="scope_rejected",
                    context={
                        "identifier": identifier,
                        "target_ctx": target_ctxs[0] if target_ctxs else None,
                        "target_ctx_candidates": list(target_ctxs),
                        "scopes": [template.admission_scope for template in identity_candidates],
                    },
                )
            ]

        if self._is_episode_requirement(requirement):
            distances = [
                scope_distance(template.admission_scope, target_ctx)
                for template, target_ctx in admitted_candidates
            ]
            if not requirement.is_qualified and distances and min(distances) > 0:
                return [
                    Blocker(
                        reason="scope_rejected",
                        context={
                            "identifier": identifier,
                            "target_ctx": target_ctxs[0] if target_ctxs else None,
                            "target_ctx_candidates": list(target_ctxs),
                            "distances": distances,
                            "policy": "unqualified_episode_requires_distance_0",
                        },
                    )
                ]

            graph = getattr(_ctx, "graph", None)
            if requirement.is_qualified and target_ctxs:
                unresolved: list[dict[str, Any]] = []
                for _template, target_ctx in admitted_candidates:
                    chain = build_plan(target_ctx, graph)
                    if not self._chain_paths_resolvable(
                        build_segments=chain,
                        target_ctx=target_ctx,
                        graph=graph,
                    ):
                        unresolved.append({"target_ctx": target_ctx, "chain": chain})
                if unresolved and len(unresolved) == len(admitted_candidates):
                    return [
                        Blocker(
                            reason="chain_unresolvable",
                            context={
                                "identifier": identifier,
                                "target_ctx": target_ctxs[0] if target_ctxs else None,
                                "target_ctx_candidates": list(target_ctxs),
                                "chains": unresolved,
                            },
                        )
                    ]

        return [
            Blocker(
                reason="no_template",
                context={
                    "identifier": identifier,
                    "target_ctx": target_ctxs[0] if target_ctxs else None,
                    "target_ctx_candidates": list(target_ctxs),
                },
            )
        ]

    def resolve_dependency(self, dependency: Dependency[PT], *, force: bool = False, _ctx=None) -> bool:
        preferred_offers = self._linked_affordance_offers(
            requirement=dependency.requirement,
            frontier=dependency.predecessor,
        )

        provider, selected_offer, _offers = self._resolve_requirement_offer(
            requirement=dependency.requirement,
            force=force,
            preferred_offers=preferred_offers,
            _ctx=_ctx,
        )
        if provider is None:
            return False

        if selected_offer is None:
            dependency.requirement.resolution_reason = "provider_none"
            return False

        if force and dependency.requirement.selected_offer_policy is ProvisionPolicy.FORCE:
            # Judgment call: force fallback is an emergency "shape only" provider.
            # We bypass requirement predicate validation here intentionally.
            if not isinstance(provider, RegistryAware):
                raise TypeError(
                    "Force fallback provider must be RegistryAware for dependency linkage"
                )
            if provider.registry is not dependency.registry:
                dependency.registry.add(provider, _ctx=_ctx)
            dependency.requirement.provider_id = provider.uid
            dependency.requirement.resolved_step = (
                getattr(_ctx, "step", None)
                if isinstance(getattr(_ctx, "step", None), int)
                else None
            )
            cursor_id = getattr(_ctx, "cursor_id", None)
            if cursor_id is None:
                cursor = getattr(_ctx, "cursor", None)
                cursor_id = getattr(cursor, "uid", None)
            dependency.requirement.resolved_cursor_id = (
                cursor_id if isinstance(cursor_id, UUID) else None
            )
            dependency.requirement.resolution_reason = "forced_fallback_resolved"
            Edge.set_successor(dependency, provider, _ctx=_ctx)
            return True

        parent = None
        try:
            parent = self._execute_build_chain(
                requirement=dependency.requirement,
                offer=selected_offer,
                graph=dependency.registry,
                _ctx=_ctx,
            )
            self._bind_dependency_provider(
                dependency=dependency,
                provider=provider,
                parent=parent,
                _ctx=_ctx,
            )
        except (ValueError, TypeError, RuntimeError):
            dependency.requirement.resolution_reason = "provider_rejected"
            return False

        if dependency.requirement.resolution_reason is None:
            dependency.requirement.resolution_reason = "resolved"
        return True

    def resolve_frontier_node(self, node: Node, *, force: bool = False, _ctx=None) -> bool:
        # Note this is not unsatisfied deps, it's anyone without a provider
        # satisfied could mean not a hard req
        open_deps = node.edges_out(Selector(has_kind=Dependency, provider=None))
        for dep in open_deps:
            self.resolve_dependency(dep, force=force, _ctx=_ctx)

        # Find unsat blockers with no provider and a hard-requirement
        unsatisfied_deps = node.edges_out(Selector(has_kind=Dependency, satisfied=False))
        if next(unsatisfied_deps, None) is not None:
            return False

        # Containers must have a reachable sink from their source.
        if isinstance(node, TraversableNode) and node.is_container:
            source = node.source
            sink = node.sink
            if source is None or sink is None:
                return False
            ns = None
            if _ctx is not None and hasattr(_ctx, "get_ns"):
                ns = dict(_ctx.get_ns(source))
            if not node.has_forward_progress(source, ns=ns):
                return False

        return True


# Register the resolution process with dispatch so it will be invoked from the phase bus
@on_provision
def provision_node(caller: Node, *, ctx, force: bool = False):
    Resolver.from_ctx(ctx).resolve_frontier_node(node=caller, force=force, _ctx=ctx)
