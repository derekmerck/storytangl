"""Address-driven template resolution and namespace management.

This module implements the core logic for materializing typed instances at
specific graph addresses using scope-based template selection.

Terminology
-----------

**address** (str)
    Target location where an instance should live in the graph hierarchy.
    Uses dotted notation for hierarchy: ``"book1.chapter2.scene3"``.
    This is a *target location*, not necessarily an existing item.

**path** (str)
    Canonical address of an existing graph item.
    Same format as address, but refers to something that already exists.
    Example: ``node.path`` → ``"book1.chapter2.scene3"``.
    Used interchangeably with "address" when referring to existing items.

**path_pattern** (str)
    Scope selector for templates using fnmatch-style patterns.
    Defines where a template can be materialized.
    Examples:
        ``"*"``
            Global (anywhere).
        ``"scene1.*"``
            Scoped to scene1 and children.
        ``"**.tavern.**"``
            Anywhere with ``tavern`` in the path.

**template.path** (str)
    Full address where a declared instance template lives.
    Set during script compilation based on template hierarchy.
    Example: Template in ``scenes.scene1.blocks.start`` → ``path="scene1.start"``.

**has_path** (criterion)
    Selection criterion for filtering graph items by their path.
    Used in queries: ``graph.find_all(has_path="scene1.*")``.

Key Concepts
------------

**Declared Instances vs Archetypes**
    - Declared instances (``declares_instance=True``) are materialized in eager mode.
    - Archetypes (``declares_instance=False``) stay in the factory for on-demand use.
    - Scene and block templates are declared instances.
    - Generic templates (like ``guard`` or ``shop``) are archetypes.

**Namespace Containers**
    - Addresses like ``"a.b.c"`` imply containers: ``"a"`` contains ``"b"`` contains ``"c"``.
    - :func:`ensure_namespace` creates these containers as generic Subgraphs.
    - Containers are created on-demand, not pre-declared.

**Template Selection**
    - Templates are selected by scope, not by parent relationships.
    - More specific scopes win over general scopes.
    - Exact path matches take priority over pattern matches.

Resolution Flow
---------------

When materializing at address ``"book1.chapter2.shop"``:

1. Ensure namespace: create containers for ``"book1"`` and ``"book1.chapter2"``.
2. Find templates: search for templates matching this address.
3. Exact match check: does any ``template.path`` equal the address?
4. Pattern match: which templates' ``path_pattern`` includes this address?
5. Rank by scope: score templates by specificity (cursor context helps).
6. Materialize: use the best-matching template to create an instance.

Key Invariants
--------------

- Address is distinct from template hierarchy.
- Scope selects templates; parentage does not.
- Parent containers are created before children.
- Exact matches win over pattern matches.
- Containers are not silently upgraded into nodes (or vice versa).

Examples
--------

Create an instance at a specific address:

.. code-block:: python

    instance = ensure_instance(
        graph,
        address="village.market.shop",
        factory=template_factory,
        world=world,
    )

List all matching templates:

.. code-block:: python

    for template, score, is_exact in iter_matching_templates(
        factory,
        address="castle.throne_room",
        selector=cursor,
    ):
        print(f"{template.label}: score={score}, exact={is_exact}")

Resolve the best template:

.. code-block:: python

    template = resolve_template_for_address(
        factory,
        address="forest.clearing",
        selector=cursor,
        strict=True,
    )
"""

from __future__ import annotations

import logging
from fnmatch import fnmatch
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tangl.story.fabula.domain_manager import DomainManager
    from tangl.core.factory import Template, TemplateFactory
    from tangl.core.graph import Graph, GraphItem, Subgraph
    from tangl.story.fabula.world import World

logger = logging.getLogger(__name__)

class AmbiguousTemplateError(ValueError):
    """Raised when multiple templates match an address equally well."""


def resolve_template_for_address(
    factory: TemplateFactory,
    address: str,
    *,
    selector: GraphItem | None = None,
    strict: bool = True,
    allow_archetypes: bool = False,
) -> Template | None:
    """Return the best template to materialize at a given address.

    Args:
        factory: Template registry to search.
        address: Target address where the instance should live.
        selector: Optional graph item for scope-aware ranking.
        strict: When True, raise if multiple templates tie for best score.

    Returns:
        The best matching template or ``None`` when no candidates match.

    Raises:
        AmbiguousTemplateError: When strict and multiple templates tie for best match.
    """

    matches = list(
        iter_matching_templates(
            factory,
            address,
            selector=selector,
            allow_archetypes=allow_archetypes,
        )
    )

    if not matches:
        _log_resolution_trace(address, [], None, strict=strict)
        return None

    matches.sort(key=lambda item: item[1])
    best_score = matches[0][1]
    best_matches = [template for template, score, _ in matches if score == best_score]
    selected = best_matches[0] if best_matches else None
    _log_resolution_trace(address, matches, selected, strict=strict)

    if strict and len(best_matches) > 1:
        raise AmbiguousTemplateError(
            f"Multiple templates match address '{address}': "
            f"{[template.label for template in best_matches]}"
        )

    return selected


def iter_matching_templates(
    factory: TemplateFactory,
    address: str,
    *,
    selector: GraphItem | None = None,
    allow_archetypes: bool = False,
) -> Iterator[tuple[Template, Any, bool]]:
    """Yield templates matching an address with their scores."""

    templates = [
        template
        for template in factory.find_all()
        if (allow_archetypes or getattr(template, "declares_instance", False))
        and not getattr(template, "script_only", False)
    ]

    exact_matches = [
        template
        for template in templates
        if _template_path_matches_address(template, address)
    ]
    if exact_matches:
        for template in exact_matches:
            yield (template, -1.0, True)
        return

    for template in templates:
        if not _template_matches_address(template, address):
            continue

        if selector is not None and hasattr(template, "scope_rank"):
            score = template.scope_rank(selector=selector)
        elif hasattr(template, "scope_specificity"):
            score = template.scope_specificity()
        else:
            score = 0.0

        yield (template, score, False)


def _log_resolution_trace(
    address: str,
    matches: list[tuple[Template, Any, bool]],
    selected: Template | None,
    *,
    strict: bool = False,
) -> None:
    """Log a detailed trace of template resolution for debugging."""

    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("=" * 60)
    logger.debug("Address Resolution Trace")
    logger.debug("=" * 60)
    logger.debug("Target address: %s", address)
    logger.debug("Strict mode: %s", strict)

    if not matches:
        logger.debug("No matching templates found")
        logger.debug("=" * 60)
        return

    logger.debug("Matching templates (%d):", len(matches))
    for index, (template, score, is_exact) in enumerate(matches, 1):
        match_type = "EXACT PATH" if is_exact else "PATTERN"
        logger.debug(
            "  %d. %s (score=%s) [%s]",
            index,
            template.label,
            score,
            match_type,
        )
        logger.debug("     path=%s", getattr(template, "path", None))
        logger.debug("     pattern=%s", getattr(template, "path_pattern", None))

    if selected is not None:
        logger.debug("Selected: %s", selected.label)
    else:
        logger.debug("Selected: None (no valid match)")

    logger.debug("=" * 60)


def _template_matches_address(template: Template, address: str) -> bool:
    """Return True when a template's scope pattern matches the address."""

    if not hasattr(template, "get_path_pattern"):
        template_path = getattr(template, "path", None)
        if template_path and template_path == address:
            return True
        label = getattr(template, "label", None)
        if label:
            return address == label or address.endswith(f".{label}")
        return False
    if _template_path_matches_address(template, address):
        return True

    pattern = template.get_path_pattern()
    if not pattern:
        return False

    if pattern == "*":
        return True

    if "**" in pattern:
        prefix = pattern.split("**", 1)[0].rstrip(".")
        if not prefix:
            return True
        return address.startswith(f"{prefix}.") or address == prefix

    if "*" in pattern:
        return fnmatch(address, pattern)

    return address == pattern or address.startswith(f"{pattern}.")


def _template_path_matches_address(template: Template, address: str) -> bool:
    """Check if template's path exactly matches the address.

    This is a strict equality check, not a suffix match.
    """

    template_path = getattr(template, "path", None)
    if not template_path:
        return False
    return template_path == address


def ensure_namespace(graph: Graph, address: str) -> Subgraph | None:
    """Ensure prefix containers exist as generic subgraphs.

    Args:
        graph: Graph to update.
        address: Address defining the namespace to ensure.

    Returns:
        The immediate parent container, or ``None`` for root-level addresses.
    """

    from tangl.core.graph import Subgraph

    prefixes = _get_prefixes(address)
    if not prefixes:
        return None

    parent: Subgraph | None = None

    for prefix in prefixes:
        existing = graph.find_subgraph(path=prefix)
        if existing is not None:
            parent = existing
            continue

        label = prefix.rsplit(".", 1)[-1] if "." in prefix else prefix

        if parent is not None:
            container = Subgraph(label=label, graph=graph)
            parent.add_member(container)
        else:
            container = graph.add_subgraph(label=label)

        parent = container

    return parent


def _get_prefixes(address: str) -> list[str]:
    """Return ordered parent prefixes for a dotted address."""

    parts = address.split(".")
    if len(parts) == 1:
        return []
    return [".".join(parts[: index + 1]) for index in range(len(parts) - 1)]


def ensure_instance(
    graph: Graph,
    address: str,
    factory: TemplateFactory,
    *,
    anchor: GraphItem | None = None,
    domain_manager: DomainManager | None = None,
    world: World | None = None,
    allow_archetypes: bool = False,
) -> GraphItem:
    """Materialize a typed instance at the given address.

    Args:
        graph: Target graph.
        address: Address where the instance should live.
        factory: Template registry for selection.
        world: World context for materialization.
        anchor: Optional selector for scope ranking.

    Returns:
        The graph item at the requested address.
    """

    existing = graph.find_node(path=address)
    if existing is not None:
        return existing

    existing_subgraph = graph.find_subgraph(path=address)
    if existing_subgraph is not None:
        template = resolve_template_for_address(
            factory,
            address,
            selector=anchor,
            strict=True,
            allow_archetypes=allow_archetypes,
        )
        if template is None:
            logger.warning(
                "Subgraph already exists at address '%s' but no template found. "
                "Returning existing subgraph.",
                address,
            )
            return existing_subgraph

        obj_cls = template.obj_cls or template.get_default_obj_cls()
        if isinstance(obj_cls, str):
            if domain_manager is None and world is not None:
                domain_manager = world.domain_manager
            if domain_manager is not None:
                obj_cls = domain_manager.resolve_class(obj_cls)

        from tangl.core.graph import Subgraph

        if obj_cls is Subgraph or (isinstance(obj_cls, type) and issubclass(obj_cls, Subgraph)):
            logger.debug(
                "Reusing existing subgraph at '%s' (template expects container type)",
                address,
            )
            return existing_subgraph
        obj_cls_name = obj_cls if isinstance(obj_cls, str) else obj_cls.__name__
        raise TypeError(
            f"Cannot create instance at '{address}': "
            f"Subgraph already exists but template expects {obj_cls_name}. "
            "This indicates a namespace container was incorrectly created at an instance address."
        )

    parent_container: Subgraph | None = None
    if "." in address:
        parent_container = ensure_namespace(graph, address)

    template = resolve_template_for_address(
        factory,
        address,
        selector=anchor,
        strict=True,
        allow_archetypes=allow_archetypes,
    )

    if template is None:
        available_templates = list(factory.find_all(declares_instance=True))
        suggestion = "Check template path_pattern scopes or add a matching template."

        if not available_templates:
            suggestion = (
                "No templates found with declares_instance=True. "
                "Check that your script defines scenes/blocks or other declared instances."
            )
        elif "." not in address:
            root_templates = [
                template
                for template in available_templates
                if "." not in getattr(template, "path", "")
            ]
            if root_templates:
                root_labels = ", ".join(template.label for template in root_templates[:5])
                suggestion = f"Available root-level templates: {root_labels}"
            else:
                suggestion = (
                    "No root-level templates found. "
                    "All templates are nested. Did you mean to use a qualified address like "
                    "'scene.block'?"
                )
        else:
            parent_addr = address.rsplit(".", 1)[0]
            similar = [
                template
                for template in available_templates
                if getattr(template, "path", "").startswith(parent_addr)
            ]
            if similar:
                similar_labels = ", ".join(template.label for template in similar[:5])
                suggestion = f"Templates in '{parent_addr}': {similar_labels}"
            else:
                available_labels = ", ".join(template.label for template in available_templates[:5])
                suggestion = (
                    f"No templates found under '{parent_addr}'. "
                    f"Available templates: {available_labels}"
                )

        raise ValueError(
            f"No template found for address '{address}'.\n"
            f"{suggestion}\n"
            "Check template path_pattern scopes or add a matching template."
        )

    if world is None:
        world = getattr(graph, "world", None)

    if domain_manager is None and world is not None:
        domain_manager = world.domain_manager

    return _materialize_at_address(
        template=template,
        address=address,
        parent=parent_container,
        graph=graph,
        domain_manager=domain_manager,
    )


def _materialize_at_address(
    *,
    template: Template,
    address: str,
    parent: Subgraph | None,
    graph: Graph,
    domain_manager: DomainManager | None = None,
) -> GraphItem:
    """Dispatch materialization for a template at an explicit address."""

    from tangl.vm.context import MaterializationContext
    from tangl.vm.dispatch import vm_dispatch
    from tangl.vm.dispatch.materialize_task import MaterializeTask

    label = address.rsplit(".", 1)[-1] if "." in address else address

    obj_cls = template.obj_cls or template.get_default_obj_cls()
    if isinstance(obj_cls, str):
        if domain_manager is None:
            raise ValueError(
                f"Cannot resolve obj_cls string '{obj_cls}' without domain_manager."
            )
        obj_cls = domain_manager.resolve_class(obj_cls)

    payload = template.unstructure_for_materialize()
    payload["obj_cls"] = obj_cls
    payload["label"] = label

    ctx = MaterializationContext(
        template=template,
        graph=graph,
        payload=payload,
        parent_container=parent,
        node=None,
    )

    caller = parent or graph
    list(vm_dispatch.dispatch(caller=caller, ctx=ctx, task=MaterializeTask.MATERIALIZE))

    if ctx.node is None:
        raise RuntimeError(
            f"Materialization failed for template '{template.label}' at '{address}'."
        )

    return ctx.node
