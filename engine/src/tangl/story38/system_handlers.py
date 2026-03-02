from __future__ import annotations

import logging
from collections.abc import Iterable as IterableABC
from typing import Any, Iterable

from tangl.core38 import Priority, Record, Selector, Singleton, TemplateRegistry, TokenCatalog
from tangl.vm38 import (
    Dependency,
    Resolver,
    on_get_template_scope_groups,
    on_get_token_catalogs,
)

from .dispatch import on_gather_ns, on_journal
from .episode import Action, Block
from .fragments import ChoiceFragment, ContentFragment, MediaFragment

logger = logging.getLogger(__name__)


@on_gather_ns
def gather_story_graph_locals(*, caller, ctx, **_kw):
    """Inject story-graph locals for current runtime scope."""
    graph = getattr(caller, "graph", None)
    locals_ = getattr(graph, "locals", None) if graph is not None else None
    if isinstance(locals_, dict) and locals_:
        return dict(locals_)
    return None


@on_gather_ns(priority=Priority.EARLY)
def gather_story_world_locals(*, caller, ctx, **_kw):
    """Inject world locals when present on attached world.

    World locals intentionally run before story-graph locals so graph values
    can override world defaults when keys overlap.
    """
    graph = getattr(caller, "graph", None)
    world = getattr(graph, "world", None) if graph is not None else None
    locals_ = getattr(world, "locals", None) if world is not None else None
    if isinstance(locals_, dict) and locals_:
        return dict(locals_)
    return None


@on_get_template_scope_groups(priority=Priority.EARLY)
def gather_story_template_scope_groups(*, caller, ctx, **_kw):
    """Contribute story template registries for the current caller."""
    graph = getattr(caller, "graph", None)
    if graph is None:
        graph = getattr(ctx, "graph", None)
    if graph is None:
        return None

    factory = getattr(graph, "factory", None)
    if isinstance(factory, TemplateRegistry):
        return [factory]

    script_manager = getattr(graph, "script_manager", None)
    template_registry = getattr(script_manager, "template_registry", None)
    if isinstance(template_registry, TemplateRegistry):
        return [template_registry]

    return None


def _registry_from_values(values: Iterable[Any]) -> TemplateRegistry | None:
    found: TemplateRegistry | None = None
    for item in values:
        registry = getattr(item, "registry", None)
        if not isinstance(registry, TemplateRegistry):
            continue
        if found is None:
            found = registry
            continue
        if found is not registry:
            return None
    return found


def _coerce_template_registry_item(value: Any) -> TemplateRegistry | None:
    if isinstance(value, TemplateRegistry):
        return value
    nested = getattr(value, "template_registry", None)
    if isinstance(nested, TemplateRegistry):
        return nested
    if isinstance(value, (str, bytes, dict)) or not isinstance(value, IterableABC):
        return None
    return _registry_from_values(value)


def _collect_provider_template_registries(
    provider: Any,
    *,
    caller: Any,
    graph: Any = None,
) -> list[TemplateRegistry]:
    if provider is None:
        return []

    raw = None
    get_scope_groups = getattr(provider, "get_template_scope_groups", None)
    if callable(get_scope_groups):
        raw = get_scope_groups(caller=caller, graph=graph)
    else:
        raw = provider

    if raw is None:
        return []
    if isinstance(raw, TemplateRegistry):
        values = [raw]
    elif isinstance(raw, (str, bytes, dict)) or not isinstance(raw, IterableABC):
        values = [raw]
    else:
        values = list(raw)

    registries: list[TemplateRegistry] = []
    seen_ids: set[int] = set()
    for value in values:
        registry = _coerce_template_registry_item(value)
        if registry is None:
            continue
        registry_id = id(registry)
        if registry_id in seen_ids:
            continue
        seen_ids.add(registry_id)
        registries.append(registry)
    return registries


@on_get_template_scope_groups(priority=Priority.LATE)
def gather_world_template_scope_groups(*, caller, ctx, **_kw):
    """Contribute world-level template registries after story-local sources."""
    graph = getattr(caller, "graph", None)
    if graph is None:
        graph = getattr(ctx, "graph", None)
    if graph is None:
        return None

    world = getattr(graph, "world", None)
    if world is None:
        return None

    providers = [
        getattr(world, "templates", None),
        world,
    ]
    registries: list[TemplateRegistry] = []
    seen_ids: set[int] = set()
    for provider in providers:
        for registry in _collect_provider_template_registries(
            provider,
            caller=caller,
            graph=graph,
        ):
            registry_id = id(registry)
            if registry_id in seen_ids:
                continue
            seen_ids.add(registry_id)
            registries.append(registry)
    return registries or None


def _coerce_token_catalog_item(value: Any) -> TokenCatalog | None:
    if isinstance(value, TokenCatalog):
        return value
    if isinstance(value, type) and issubclass(value, Singleton):
        return TokenCatalog(wst=value)
    return None


def _collect_provider_token_catalogs(
    provider: Any,
    *,
    caller: Any,
    requirement: Any = None,
    graph: Any = None,
) -> list[TokenCatalog]:
    if provider is None:
        return []

    raw = None
    get_catalogs = getattr(provider, "get_token_catalogs", None)
    if callable(get_catalogs):
        raw = get_catalogs(caller=caller, requirement=requirement, graph=graph)
    else:
        get_tokenizable = getattr(provider, "get_tokenizable", None)
        if callable(get_tokenizable):
            raw = get_tokenizable()

    if raw is None:
        return []
    if isinstance(raw, (str, bytes, dict)):
        return []
    if isinstance(raw, Iterable):
        values = list(raw)
    else:
        values = [raw]

    catalogs: list[TokenCatalog] = []
    for value in values:
        catalog = _coerce_token_catalog_item(value)
        if catalog is not None:
            catalogs.append(catalog)
    return catalogs


@on_get_token_catalogs(priority=Priority.LATE)
def gather_world_token_catalogs(*, caller, requirement=None, ctx, **_kw):
    """Contribute token catalogs from world-level asset/domain providers."""
    graph = getattr(caller, "graph", None)
    if graph is None:
        graph = getattr(ctx, "graph", None)
    if graph is None:
        return None

    world = getattr(graph, "world", None)
    if world is None:
        return None

    providers = [
        getattr(world, "assets", None),
        getattr(world, "domain", None),
        world,
    ]
    catalogs: list[TokenCatalog] = []
    for provider in providers:
        catalogs.extend(
            _collect_provider_token_catalogs(
                provider,
                caller=caller,
                requirement=requirement,
                graph=graph,
            )
        )
    return catalogs or None


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive fallback
        return "{" + key + "}"


def _render_block_content(block: Block, *, ctx) -> str:
    """Best-effort templating for block content against the gathered namespace."""
    content = block.content or ""
    if not content:
        return ""
    if ctx is None or not hasattr(ctx, "get_ns"):
        return content
    try:
        ns = dict(ctx.get_ns(block))
        return content.format_map(_SafeFormatDict(ns))
    except Exception:
        return content


def _hard_unresolved_dependencies(*, edge: Action) -> list[Dependency]:
    """Return unresolved hard dependencies on an action successor."""
    successor = edge.successor
    if successor is None:
        return []

    unresolved = successor.edges_out(Selector(has_kind=Dependency, satisfied=False))
    return [
        dep
        for dep in unresolved
        if bool(getattr(dep.requirement, "hard_requirement", False))
    ]


def _destination_dependency(*, edge: Action) -> Dependency | None:
    """Return destination dependency edge when successor is unresolved."""
    graph = getattr(edge, "graph", None)
    if graph is None:
        return None
    deps = list(graph.find_edges(Selector(has_kind=Dependency, predecessor=edge)))
    for dep in deps:
        if dep.get_label() == "destination":
            return dep
    return deps[0] if deps else None


def _preview_destination_viability(*, edge: Action, ctx):
    dep = _destination_dependency(edge=edge)
    if dep is None or dep.requirement.satisfied:
        return None
    try:
        resolver = Resolver.from_ctx(ctx)
    except (TypeError, ValueError, LookupError) as exc:
        logger.debug("Resolver preview unavailable for edge=%s", edge, exc_info=exc)
        return None
    return resolver.preview_requirement(dep.requirement, _ctx=ctx)


def _preview_blockers(preview) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for blocker in getattr(preview, "blockers", []) or []:
        blockers.append(
            {
                "type": "provision",
                "reason": blocker.reason,
                "context": dict(blocker.context or {}),
            }
        )
    return blockers


def _choice_unavailable_reason(*, edge: Action, ctx) -> str | None:
    """Return a coarse reason for unavailable choices."""
    if edge.successor is None:
        preview = _preview_destination_viability(edge=edge, ctx=ctx)
        if preview is not None and preview.viable:
            return None
        return "missing_successor"

    # Hard unresolved dependencies block choice availability regardless of guard predicates.
    if _hard_unresolved_dependencies(edge=edge):
        return "missing_dependency"

    if not edge.available(ctx=ctx):
        return "guard_failed_or_unavailable"

    return None


def _dependency_blocker(dep: Dependency) -> dict[str, Any]:
    """Serialize one dependency blocker with standardized resolver diagnostics."""
    requirement = dep.requirement
    return {
        "type": "dependency",
        "dependency_id": str(dep.uid),
        "label": dep.get_label(),
        "hard_requirement": requirement.hard_requirement,
        "resolution_reason": requirement.resolution_reason,
        "resolution_meta": requirement.resolution_meta,
    }


def _choice_blockers(*, edge: Action, ctx) -> list[dict[str, Any]]:
    """Return structured blocker diagnostics for an unavailable choice edge."""
    if edge.successor is None:
        preview = _preview_destination_viability(edge=edge, ctx=ctx)
        if preview is not None:
            if preview.viable:
                return []
            preview_blockers = _preview_blockers(preview)
            if preview_blockers:
                return preview_blockers
        return [{"type": "edge", "reason": "missing_successor"}]

    blockers = [_dependency_blocker(dep) for dep in _hard_unresolved_dependencies(edge=edge)]
    if blockers:
        return blockers

    if not edge.available(ctx=ctx):
        return [{"type": "edge", "reason": "guard_failed_or_unavailable"}]

    return []


def _merge_fragment_batches(*batches: Any) -> list[Record]:
    merged: list[Record] = []
    for batch in batches:
        if batch is None:
            continue
        if isinstance(batch, Record):
            merged.append(batch)
            continue
        if isinstance(batch, list):
            merged.extend(batch)
            continue
        merged.extend(list(batch))
    return merged


@on_journal(priority=Priority.EARLY)
def render_block_content(*, caller, ctx, **_kw):
    """Render block narrative text into content fragments."""
    if not isinstance(caller, Block):
        return None

    rendered_content = _render_block_content(caller, ctx=ctx)
    if rendered_content:
        return ContentFragment(content=rendered_content, source_id=caller.uid)
    return None


@on_journal(priority=Priority.NORMAL)
def render_block_media(*, caller, ctx, **_kw):
    """Render block media payloads into media fragments."""
    if not isinstance(caller, Block):
        return None

    fragments: list[MediaFragment] = []
    for media_item in caller.media:
        payload = media_item if isinstance(media_item, dict) else {"value": media_item}
        fragments.append(MediaFragment(source_id=caller.uid, payload=payload))

    return fragments or None


@on_journal(priority=Priority.LATE)
def render_block_choices(*, caller, ctx, **_kw):
    """Render block outbound actions into choice fragments."""
    if not isinstance(caller, Block):
        return None

    fragments: list[ChoiceFragment] = []

    for edge in caller.edges_out(Selector(has_kind=Action, trigger_phase=None)):
        reason = _choice_unavailable_reason(edge=edge, ctx=ctx)
        available = reason is None
        blockers = [] if available else _choice_blockers(edge=edge, ctx=ctx)
        fragments.append(
            ChoiceFragment(
                edge_id=edge.uid,
                text=edge.text or edge.get_label(),
                available=available,
                unavailable_reason=(None if available else reason),
                blockers=blockers or None,
                accepts=(dict(edge.accepts) if isinstance(edge.accepts, dict) else None),
                ui_hints=(dict(edge.ui_hints) if isinstance(edge.ui_hints, dict) else None),
            )
        )

    return fragments or None


def render_block(*, caller, ctx, **_kw):
    """Compatibility facade for block journal rendering.

    This wrapper preserves direct-call behavior while journal rendering is split
    into composable handlers (`render_block_content`, `render_block_media`,
    `render_block_choices`) registered through dispatch.
    """
    if not isinstance(caller, Block):
        return None

    fragments = _merge_fragment_batches(
        render_block_content(caller=caller, ctx=ctx),
        render_block_media(caller=caller, ctx=ctx),
        render_block_choices(caller=caller, ctx=ctx),
    )
    return fragments or None
