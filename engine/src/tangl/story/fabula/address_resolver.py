"""Address-driven template resolution and namespace helpers."""

from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tangl.story.fabula.domain_manager import DomainManager
    from tangl.core.factory import Template, TemplateFactory
    from tangl.core.graph import Graph, GraphItem, Subgraph
    from tangl.story.fabula.world import World


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

    candidates: list[tuple[Template, Any]] = []

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
        templates = exact_matches

    for template in templates:
        if not _template_matches_address(template, address):
            continue

        if selector is not None and hasattr(template, "scope_rank"):
            score = template.scope_rank(selector=selector)
        elif hasattr(template, "scope_specificity"):
            score = template.scope_specificity()
        else:
            score = 0

        candidates.append((template, score))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[1])

    if strict and len(candidates) > 1:
        best_score = candidates[0][1]
        tied = [template for template, score in candidates if score == best_score]
        if len(tied) > 1:
            raise AmbiguousTemplateError(
                f"Multiple templates match address '{address}': "
                f"{[template.label for template in tied]}"
            )

    return candidates[0][0]


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
    template_path = getattr(template, "path", None)
    if not template_path:
        return False
    if template_path == address:
        return True
    return template_path.endswith(f".{address}")


def ensure_namespace(graph: Graph, address: str) -> Subgraph:
    """Ensure prefix containers exist as generic subgraphs.

    Args:
        graph: Graph to update.
        address: Address defining the namespace to ensure.

    Returns:
        The subgraph container corresponding to the full address.
    """

    from tangl.core.graph import Subgraph

    prefixes = _get_prefixes(address)
    parent: Subgraph | None = None

    for prefix in prefixes:
        existing = graph.find_subgraph(path=prefix)
        if existing is not None:
            parent = existing
            continue

        label = prefix.rsplit(".", 1)[-1] if "." in prefix else prefix
        container = graph.add_subgraph(label=label)

        if parent is not None:
            parent.add_member(container)

        parent = container

    if parent is None:
        raise ValueError(f"No prefixes resolved for address '{address}'")

    return parent


def _get_prefixes(address: str) -> list[str]:
    """Return ordered prefix addresses for a dotted address."""

    parts = address.split(".")
    return [".".join(parts[: index + 1]) for index in range(len(parts))]


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

    parent_container: Subgraph | None = None
    if "." in address:
        parent_container = ensure_namespace(graph, address.rsplit(".", 1)[0])

    template = resolve_template_for_address(
        factory,
        address,
        selector=anchor,
        strict=True,
        allow_archetypes=allow_archetypes,
    )

    if template is None:
        raise ValueError(
            f"No template found for address '{address}'. "
            "Check for a template with a matching scope pattern."
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
