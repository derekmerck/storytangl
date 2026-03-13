"""Default story dispatch handlers for namespace gathering and journaling.

This module registers the story-layer handlers that:

* contribute story and world locals during gathered namespace assembly,
* contribute template scopes and token catalogs for runtime provisioning, and
* turn a :class:`~tangl.story.episode.block.Block` cursor into journal
  fragments during the JOURNAL phase.

These handlers define story-specific policy on top of the generic dispatch and
resolver mechanisms in :mod:`tangl.vm`.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from tangl.core import Priority, Record, Selector, TemplateRegistry
from tangl.discourse import DialogHandler
from tangl.media import get_system_resource_manager
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaDep
from tangl.media.story_media import get_story_resource_manager
from tangl.vm import (
    Affordance,
    Dependency,
    Resolver,
    do_compose_journal,
    on_get_media_inventories,
    on_provision,
    on_get_template_scope_groups,
    on_get_token_catalogs,
)

from .dispatch import on_compose_journal, on_gather_ns, on_journal
from .episode import Action, Block, MenuBlock
from .fragments import ChoiceFragment, ContentFragment, MediaFragment
from .provider_collection import (
    collect_media_inventories,
    collect_template_registries,
    collect_token_catalogs,
)

logger = logging.getLogger(__name__)


@on_gather_ns
def gather_story_graph_locals(*, caller, ctx, **_kw):
    """Inject story-graph locals into the assembled runtime namespace."""
    graph = getattr(caller, "graph", None)
    locals_ = getattr(graph, "locals", None) if graph is not None else None
    if isinstance(locals_, dict) and locals_:
        return dict(locals_)
    return None


@on_gather_ns(priority=Priority.EARLY)
def gather_story_world_locals(*, caller, ctx, **_kw):
    """Inject world locals into the assembled runtime namespace.

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
    registries = collect_template_registries(
        providers,
        caller=caller,
        graph=graph,
    )
    return registries or None


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
    catalogs = collect_token_catalogs(
        providers,
        caller=caller,
        requirement=requirement,
        graph=graph,
    )
    return catalogs or None


@on_get_media_inventories(priority=Priority.FIRST)
def gather_story_media_inventories(*, caller, requirement=None, ctx, **_kw):
    """Contribute story-local media inventory ahead of world/system scopes."""
    graph = getattr(caller, "graph", None) or getattr(ctx, "graph", None)
    if graph is None:
        return None

    manager = getattr(graph, "story_resources", None)
    if manager is None and getattr(graph, "story_id", None) is not None:
        manager = get_story_resource_manager(graph.story_id, create=False)
        if manager is not None:
            graph.story_resources = manager

    inventories = collect_media_inventories(
        [manager],
        caller=caller,
        requirement=requirement,
        graph=graph,
        scope="story",
    )
    return inventories or None


@on_get_media_inventories(priority=Priority.LATE)
def gather_world_media_inventories(*, caller, requirement=None, ctx, **_kw):
    """Contribute world-scoped media inventories after story-local sources."""
    graph = getattr(caller, "graph", None) or getattr(ctx, "graph", None)
    if graph is None:
        return None

    world = getattr(graph, "world", None)
    if world is None:
        return None

    providers = [
        getattr(world, "resources", None),
        world,
    ]
    inventories = collect_media_inventories(
        providers,
        caller=caller,
        requirement=requirement,
        graph=graph,
        scope="world",
    )
    return inventories or None


@on_get_media_inventories(priority=Priority.LAST)
def gather_system_media_inventories(*, caller, requirement=None, ctx, **_kw):
    """Contribute shared system media inventory last."""
    graph = getattr(caller, "graph", None) or getattr(ctx, "graph", None)
    inventories = collect_media_inventories(
        [get_system_resource_manager()],
        caller=caller,
        requirement=requirement,
        graph=graph,
        scope="sys",
    )
    return inventories or None


def _has_tags(value: Any, *tags: str) -> bool:
    actual = getattr(value, "tags", set()) or set()
    return set(tags).issubset(actual)


def _clear_dynamic_menu_actions(menu: MenuBlock, *, ctx) -> None:
    graph = getattr(menu, "graph", None)
    if graph is None:
        return

    for edge in list(menu.edges_out(Selector(has_kind=Action, trigger_phase=None))):
        if _has_tags(edge, "dynamic", "fanout", "menu"):
            graph.remove(edge.uid, _ctx=ctx)


def _iter_menu_affordances(menu: MenuBlock):
    for affordance in list(menu.edges_out(Selector(has_kind=Affordance))):
        if _has_tags(affordance, "dynamic", "fanout"):
            yield affordance


@on_provision(
    wants_caller_kind=MenuBlock,
    wants_exact_kind=False,
    priority=Priority.LATE,
)
def project_menu_affordances(*, caller, ctx, **_kw):
    """Project fanout-produced affordances into ordinary choice edges."""
    if not isinstance(caller, MenuBlock):
        return None
    graph = getattr(caller, "graph", None)
    if bool(getattr(graph, "frozen_shape", False)):
        return None
    if not caller.auto_provision:
        return None

    _clear_dynamic_menu_actions(caller, ctx=ctx)

    for index, affordance in enumerate(_iter_menu_affordances(caller)):
        provider = affordance.successor
        if provider is None:
            provider = affordance.provider
        if provider is None:
            continue

        Action(
            registry=caller.graph,
            label=f"menu_{caller.get_label()}_{index}",
            predecessor_id=caller.uid,
            successor_id=provider.uid,
            text=MenuBlock.action_text_for(provider),
            tags={"dynamic", "fanout", "menu"},
        )
    return None


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


def _coerce_media_type(value: Any) -> MediaDataType:
    if isinstance(value, MediaDataType):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return MediaDataType(value)
        except ValueError:
            return MediaDataType(value.strip("."))
    return MediaDataType.MEDIA


def _media_type_for_item(item: dict[str, Any]) -> MediaDataType:
    explicit = item.get("content_type") or item.get("media_type") or item.get("kind")
    if explicit is not None:
        return _coerce_media_type(explicit)

    for key in ("url", "name", "src"):
        value = item.get(key)
        if isinstance(value, str) and "." in value:
            return MediaDataType.from_path(value)
    data = item.get("data")
    if isinstance(data, str) and data.lstrip().startswith("<svg"):
        return MediaDataType.VECTOR
    return MediaDataType.MEDIA


def _scope_from_provider(provider: Any, *, default: str = "world") -> str:
    tags = getattr(provider, "tags", set()) or set()
    for tag in tags:
        if isinstance(tag, str) and tag.startswith("scope:"):
            return tag.split(":", 1)[1]
    return default


def _unresolved_media_placeholder(
    *,
    caller: Block,
    payload: dict[str, Any],
    dependency: MediaDep | None,
    source_kind: str,
    unresolved_reason: str | None = None,
) -> MediaFragment:
    scope = payload.get("scope") or "world"
    reason = unresolved_reason or "unresolved_media"
    resolution_meta: dict[str, Any] | None = None

    if isinstance(dependency, MediaDep) and unresolved_reason is None:
        scope = dependency.scope or scope
        reason = dependency.requirement.resolution_reason or reason
        if isinstance(dependency.requirement.resolution_meta, dict):
            resolution_meta = dict(dependency.requirement.resolution_meta)
    elif source_kind == "potential" and unresolved_reason is None:
        reason = "unsupported_media_spec"

    placeholder_payload = {
        "name": payload.get("name") or payload.get("label"),
        "source_kind": source_kind,
        "unresolved_reason": reason,
    }
    if payload.get("facet") is not None:
        placeholder_payload["facet"] = payload.get("facet")
    if payload.get("subject") is not None:
        placeholder_payload["subject"] = payload.get("subject")
    if resolution_meta:
        placeholder_payload["resolution_meta"] = resolution_meta

    return MediaFragment(
        source_id=caller.uid,
        media_role=payload.get("media_role"),
        content=placeholder_payload,
        content_format="json",
        content_type=_media_type_for_item(payload),
        text=payload.get("text"),
        scope=scope,
    )


def _maybe_compose_fragments(*, caller: Block, ctx, fragments: list[Record]) -> list[Record]:
    """Run optional post-merge journal composition when ctx supports dispatch."""
    if not fragments:
        return fragments

    has_authorities = callable(getattr(ctx, "get_authorities", None))
    has_inline = callable(getattr(ctx, "get_inline_behaviors", None))
    if not has_authorities or not has_inline:
        return fragments

    composed = do_compose_journal(caller, ctx=ctx, fragments=list(fragments))
    if composed is None:
        return fragments
    if isinstance(composed, Record):
        return [composed]
    return list(composed)


def _json_media_payload(value: Any) -> Any:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="python")
    if isinstance(value, dict):
        return dict(value)
    return value


def _is_empty_media_payload(value: Any) -> bool:
    if value is None:
        return True
    payload = _json_media_payload(value)
    if isinstance(payload, dict):
        metadata_only_keys = {
            "attitude",
            "content_type",
            "media_role",
            "pose",
            "role",
            "scope",
            "source",
            "source_kind",
        }
        content_values = [
            item for key, item in payload.items()
            if key not in metadata_only_keys
        ]
        return not any(bool(item) for item in content_values)
    return False


def _render_facet_media(
    *,
    caller: Block,
    payload: dict[str, Any],
    ctx,
    ns: dict[str, Any],
) -> Record:
    subject_key = payload.get("subject")
    subject = ns.get(subject_key) if isinstance(subject_key, str) else subject_key
    facet = str(payload.get("facet") or "").strip().lower()

    if subject is None:
        fallback = payload.get("fallback_text") or payload.get("text")
        if isinstance(fallback, str) and fallback.strip():
            return ContentFragment(content=fallback, source_id=caller.uid)
        unresolved_payload = dict(payload)
        unresolved_payload.setdefault("name", f"{subject_key or 'unknown'}:{facet or 'facet'}")
        return _unresolved_media_placeholder(
            caller=caller,
            payload=unresolved_payload,
            dependency=None,
            source_kind="facet",
            unresolved_reason="missing_facet_subject",
        )

    adapter_name = {
        "look": "adapt_look_media_spec",
        "outfit": "adapt_outfit_media_spec",
        "ornamentation": "adapt_ornament_media_spec",
    }.get(facet)
    adapter = getattr(subject, adapter_name, None) if adapter_name is not None else None
    if not callable(adapter):
        fallback = payload.get("fallback_text") or payload.get("text")
        if isinstance(fallback, str) and fallback.strip():
            return ContentFragment(content=fallback, source_id=caller.uid)
        unresolved_payload = dict(payload)
        unresolved_payload.setdefault(
            "name",
            f"{subject_key or getattr(subject, 'label', 'subject')}:{facet or 'facet'}",
        )
        return _unresolved_media_placeholder(
            caller=caller,
            payload=unresolved_payload,
            dependency=None,
            source_kind="facet",
            unresolved_reason="unsupported_facet",
        )

    adapter_kwargs: dict[str, Any] = {"ctx": ctx}
    if payload.get("media_role") is not None:
        adapter_kwargs["media_role"] = payload.get("media_role")
    if facet == "look":
        if payload.get("attitude") is not None:
            adapter_kwargs["attitude"] = payload.get("attitude")
        if payload.get("pose") is not None:
            adapter_kwargs["pose"] = payload.get("pose")

    facet_payload = adapter(**adapter_kwargs)
    if _is_empty_media_payload(facet_payload):
        fallback = payload.get("fallback_text") or payload.get("text")
        if isinstance(fallback, str) and fallback.strip():
            return ContentFragment(content=fallback, source_id=caller.uid)
        unresolved_payload = dict(payload)
        unresolved_payload.setdefault(
            "name",
            f"{subject_key or getattr(subject, 'label', 'subject')}:{facet or 'facet'}",
        )
        return _unresolved_media_placeholder(
            caller=caller,
            payload=unresolved_payload,
            dependency=None,
            source_kind="facet",
            unresolved_reason="empty_facet_payload",
        )

    content = _json_media_payload(facet_payload)
    content_media_role = content.get("media_role") if isinstance(content, dict) else None
    return MediaFragment(
        source_id=caller.uid,
        media_role=content_media_role or payload.get("media_role"),
        content=content,
        content_format="json",
        content_type=_media_type_for_item(payload),
        text=payload.get("text"),
        scope=payload.get("scope") or "world",
    )


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

    graph = getattr(caller, "graph", None)
    fragments: list[Record] = []
    facet_ns: dict[str, Any] | None = None
    for media_item in caller.media:
        payload = media_item if isinstance(media_item, dict) else {"value": media_item}
        source_kind = payload.get("source_kind")

        dependency_id = payload.get("dependency_id")
        dependency = graph.get(dependency_id) if graph is not None and dependency_id is not None else None
        if isinstance(dependency, MediaDep) and dependency.provider is not None:
            provider = dependency.provider
            fragments.append(
                MediaFragment(
                    source_id=caller.uid,
                    media_role=payload.get("media_role"),
                    content=provider,
                    content_format="rit",
                    content_type=getattr(provider, "data_type", MediaDataType.MEDIA),
                    text=payload.get("text"),
                    scope=dependency.scope or _scope_from_provider(provider),
                )
            )
            continue

        if source_kind == "url" and payload.get("url") is not None:
            fragments.append(
                MediaFragment(
                    source_id=caller.uid,
                    media_role=payload.get("media_role"),
                    content=str(payload.get("url")),
                    content_format="url",
                    content_type=_media_type_for_item(payload),
                    text=payload.get("text"),
                    scope=payload.get("scope") or "external",
                )
            )
            continue

        if source_kind == "data" and payload.get("data") is not None:
            fragments.append(
                MediaFragment(
                    source_id=caller.uid,
                    media_role=payload.get("media_role"),
                    content=payload.get("data"),
                    content_format="data",
                    content_type=_media_type_for_item(payload),
                    text=payload.get("text"),
                    scope=payload.get("scope"),
                )
            )
            continue

        if source_kind == "facet":
            if facet_ns is None:
                if ctx is None or not hasattr(ctx, "get_ns"):
                    facet_ns = {}
                else:
                    facet_ns = dict(ctx.get_ns(caller))
            fragments.append(
                _render_facet_media(
                    caller=caller,
                    payload=payload,
                    ctx=ctx,
                    ns=facet_ns,
                )
            )
            continue

        if source_kind in {"inventory", "potential"}:
            fallback = payload.get("fallback_text") or payload.get("text")
            if isinstance(fallback, str) and fallback.strip():
                fragments.append(ContentFragment(content=fallback, source_id=caller.uid))
            else:
                fragments.append(
                    _unresolved_media_placeholder(
                        caller=caller,
                        payload=payload,
                        dependency=dependency if isinstance(dependency, MediaDep) else None,
                        source_kind=str(source_kind),
                    )
                )
            continue

        fragments.append(
            MediaFragment(
                source_id=caller.uid,
                media_role=payload.get("media_role"),
                content=payload,
                content_format="json",
                content_type=_media_type_for_item(payload),
                text=payload.get("text"),
                scope=payload.get("scope") or "world",
            )
        )

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
    `render_block_choices`) registered through dispatch, then optionally passed
    through the post-merge ``compose_journal`` seam when the context supports
    dispatch authorities.
    """
    if not isinstance(caller, Block):
        return None

    fragments = _merge_fragment_batches(
        render_block_content(caller=caller, ctx=ctx),
        render_block_media(caller=caller, ctx=ctx),
        render_block_choices(caller=caller, ctx=ctx),
    )
    fragments = _maybe_compose_fragments(caller=caller, ctx=ctx, fragments=fragments)
    return fragments or None


@on_compose_journal(priority=Priority.EARLY)
def compose_dialog_markup(*, caller, ctx, fragments, **_kw):
    """Promote explicit dialog micro-block syntax into attributed fragments."""
    if not isinstance(caller, Block):
        return None

    ns: dict[str, Any] | None = None
    if ctx is not None and hasattr(ctx, "get_ns"):
        ns = dict(ctx.get_ns(caller))

    composed: list[Record] = []
    changed = False
    for fragment in fragments:
        if (
            isinstance(fragment, ContentFragment)
            and getattr(fragment, "fragment_type", "content") == "content"
            and isinstance(fragment.content, str)
            and DialogHandler.has_mu_blocks(fragment.content)
        ):
            mu_blocks = DialogHandler.parse(
                fragment.content,
                source_id=getattr(fragment, "source_id", None),
                ns=ns,
                ctx=ctx,
            )
            rendered = DialogHandler.render(mu_blocks)
            for rendered_fragment in rendered:
                updated_tags = set(rendered_fragment.tags or set())
                if getattr(fragment, "tags", None):
                    updated_tags |= set(fragment.tags)

                update: dict[str, Any] = {
                    "step": fragment.step,
                    "tags": updated_tags,
                }
                if getattr(fragment, "origin_id", None) is not None:
                    update["origin_id"] = fragment.origin_id

                composed.append(rendered_fragment.model_copy(update=update))
            changed = True
            continue

        composed.append(fragment)

    return composed if changed else None
