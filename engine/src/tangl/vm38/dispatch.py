# tangl/vm38/dispatch.py
"""Phase bus hooks for the VM pipeline.

This module provides the registration (``on_*``) and execution (``do_*``) surface
for every phase in the resolution pipeline, plus the namespace gathering hook
that composes scoped context from the hierarchy.

Design Principle — Explicit Names, DRY Bodies
----------------------------------------------
Each ``on_*`` / ``do_*`` pair is an explicitly named module-level function (for IDE
support, import clarity, and grep-ability) but the body is generated from a shared
helper keyed by task name and aggregation mode.

The ``on_resolve`` / ``do_resolve`` hook is separate because it has a different call
signature (takes ``requirement`` + ``offers``, not ``caller``).

The ``on_gather_ns`` / ``do_gather_ns`` hook family is separate because it
composes per-entity namespace maps with dispatch contributions.

See Also
--------
:mod:`tangl.vm38.resolution_phase`
    Phase ordering and semantics.
:mod:`tangl.core38.behavior`
    ``BehaviorRegistry`` and ``CallReceipt`` aggregation primitives.
:mod:`tangl.vm38.runtime.frame`
    Consumer of the ``do_*`` functions.
"""

from __future__ import annotations

import logging
from collections import ChainMap
from collections.abc import Iterable as IterableABC, Mapping
from typing import Any, Callable, Iterable, TYPE_CHECKING

from tangl.core38 import BehaviorRegistry, CallReceipt, DispatchLayer, Node, Record, Selector
if TYPE_CHECKING:
    from .provision import Requirement, ProvisionOffer
    from .traversable import TraversableNode, TraversableEdge, AnyTraversableEdge

    Fragment = Record
    Patch = Record

logger = logging.getLogger(__name__)

Fragment = Record
Patch = Record

dispatch = BehaviorRegistry(
    label="vm_dispatch",
    default_dispatch_layer=DispatchLayer.SYSTEM,
)
"""Module-level behavior registry for VM phase hooks.

All ``on_*`` registrations go here.  ``do_*`` functions include this registry
automatically alongside any registries provided by the dispatch context.
"""


# ---------------------------------------------------------------------------
# Hook generation helpers
# ---------------------------------------------------------------------------

def _validate_dispatch_ctx(ctx: Any) -> None:
    """Raise ``TypeError`` when ctx lacks dispatch protocol methods."""
    has_authorities = callable(getattr(ctx, "get_authorities", None)) or callable(
        getattr(ctx, "get_registries", None)
    )
    has_inline = callable(getattr(ctx, "get_inline_behaviors", None))
    if not has_authorities or not has_inline:
        raise TypeError(
            "Dispatch context must provide get_authorities()/get_registries() "
            "and get_inline_behaviors()"
        )
    return None


def _make_on_hook(task: str) -> Callable:
    """Create a registration decorator for a phase task.

    Works as both ``@on_validate`` and ``@on_validate(priority=EARLY)``.
    """
    def on_hook(func=None, **kwargs):
        if func is None:
            return lambda f: dispatch.register(func=f, task=task, **kwargs)
        return dispatch.register(func=func, task=task, **kwargs)
    on_hook.__name__ = f"on_{task}"
    on_hook.__doc__ = f"Register a handler for the ``{task}`` task."
    return on_hook


def _run_task(task: str, *, caller, ctx, **kwargs) -> list[CallReceipt]:
    _validate_dispatch_ctx(ctx)
    receipts = dispatch.execute_all(
        task=task,
        call_kwargs={"caller": caller, **kwargs},
        ctx=ctx,
        selector=Selector(caller_kind=type(caller)),
    )
    return list(receipts)


def _assert_redirect_result(value, *, task: str):
    if value is None:
        return None
    from .traversable import AnonymousEdge, TraversableEdge
    if isinstance(value, (AnonymousEdge, TraversableEdge)):
        return value
    raise TypeError(f"{task} must return a traversable edge or None, got {type(value)!r}")


def _assert_journal_result(value):
    if value is None:
        return None
    if isinstance(value, Record):
        return value
    if isinstance(value, IterableABC) and not isinstance(value, (str, bytes, dict)):
        fragments = list(value)
        if all(isinstance(fragment, Record) for fragment in fragments):
            return fragments
    raise TypeError(
        "render_journal must return Record | Iterable[Record] | None"
    )


def _assert_patch_result(value):
    if value is None or isinstance(value, Record):
        return value
    raise TypeError(f"finalize_step must return Record | None, got {type(value)!r}")


# ---------------------------------------------------------------------------
# Generated phase hooks
# ---------------------------------------------------------------------------

# Registration hooks
on_validate  = _make_on_hook("validate_edge")
on_provision = _make_on_hook("provision_node")
on_prereqs   = _make_on_hook("get_prereqs")
on_update    = _make_on_hook("apply_update")
on_journal   = _make_on_hook("render_journal")
on_finalize  = _make_on_hook("finalize_step")
on_postreqs  = _make_on_hook("get_postreqs")

# Execution hooks with explicit phase-level type contracts
def do_validate(caller, *, ctx, **kwargs) -> bool:
    result = CallReceipt.all_true(*_run_task("validate_edge", caller=caller, ctx=ctx, **kwargs))
    if not isinstance(result, bool):
        raise TypeError(f"validate_edge must return bool, got {type(result)!r}")
    return result


def do_provision(caller, *, ctx, **kwargs) -> None:
    results = CallReceipt.gather_results(*_run_task("provision_node", caller=caller, ctx=ctx, **kwargs))
    if results:
        raise TypeError(
            "provision_node handlers must return None; non-None planning receipts are not supported in vm38"
        )
    return None


def do_prereqs(caller, *, ctx, **kwargs):
    result = CallReceipt.first_result(*_run_task("get_prereqs", caller=caller, ctx=ctx, **kwargs))
    return _assert_redirect_result(result, task="get_prereqs")


def do_update(caller, *, ctx, **kwargs) -> None:
    results = CallReceipt.gather_results(*_run_task("apply_update", caller=caller, ctx=ctx, **kwargs))
    if results:
        raise TypeError(
            "apply_update handlers must return None; update side effects must be in-place"
        )
    return None


def do_journal(caller, *, ctx, **kwargs):
    receipts = _run_task("render_journal", caller=caller, ctx=ctx, **kwargs)
    results = CallReceipt.gather_results(*receipts)
    if not results:
        return None

    merged: list[Record] = []
    for value in results:
        normalized = _assert_journal_result(value)
        if normalized is None:
            continue
        if isinstance(normalized, Record):
            merged.append(normalized)
            continue
        merged.extend(normalized)

    if not merged:
        return None
    if len(merged) == 1:
        return merged[0]
    return merged


def do_finalize(caller, *, ctx, **kwargs):
    result = CallReceipt.last_result(*_run_task("finalize_step", caller=caller, ctx=ctx, **kwargs))
    return _assert_patch_result(result)


def do_postreqs(caller, *, ctx, **kwargs):
    result = CallReceipt.first_result(*_run_task("get_postreqs", caller=caller, ctx=ctx, **kwargs))
    return _assert_redirect_result(result, task="get_postreqs")


# ---------------------------------------------------------------------------
# Namespace gathering hook — two-phase semantic
# ---------------------------------------------------------------------------

def on_gather_ns(func=None, **kwargs):
    """Register a namespace contributor for the ``gather_ns`` task.

    Use ``has_kind=Type`` to apply subclass-based caller filtering.
    """
    has_kind = kwargs.pop("has_kind", None)
    if has_kind is not None:
        kwargs.setdefault("wants_caller_kind", has_kind)
        kwargs.setdefault("wants_exact_kind", False)

    if func is None:
        return lambda f: dispatch.register(func=f, task="gather_ns", **kwargs)
    return dispatch.register(func=func, task="gather_ns", **kwargs)


def _coerce_ns_layers(value: Any, *, source: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        if not value:
            return []
        if all(isinstance(item, Mapping) for item in value):
            return [item for item in value if item]
        raise TypeError(f"{source} must return mappings only, got {type(value)!r}")
    if isinstance(value, ChainMap):
        return [layer for layer in value.maps if layer]
    if isinstance(value, Mapping):
        return [value] if value else []
    raise TypeError(f"{source} must return Mapping | ChainMap | None, got {type(value)!r}")


def _merge_nested_layers(
    layers: list[Mapping[str, Any]],
    *,
    nested_keys: tuple[str, ...] = ("roles", "settings"),
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for nested_key in nested_keys:
        combined: dict[str, Any] = {}
        for layer in reversed(layers):
            nested = layer.get(nested_key)
            if isinstance(nested, Mapping):
                combined.update(dict(nested))
        if combined:
            merged[nested_key] = combined
    return merged


def do_gather_ns(node: Node, *, ctx) -> ChainMap[str, Any]:
    """Build a scoped namespace in two phases.

    Phase 1: collect ``get_ns()`` from caller and its ancestor chain.
    Phase 2: execute immediate-caller ``gather_ns`` dispatch handlers.
    """
    _validate_dispatch_ctx(ctx)

    ancestors = list(node.ancestors) if hasattr(node, "ancestors") else [node]
    layers: list[Mapping[str, Any]] = []

    for ancestor in ancestors:
        get_ns = getattr(ancestor, "get_ns", None)
        if not callable(get_ns):
            continue
        layers.extend(
            _coerce_ns_layers(get_ns(), source=f"{type(ancestor).__name__}.get_ns"),
        )

    receipts = dispatch.execute_all(
        task="gather_ns",
        call_kwargs={"caller": node},
        ctx=ctx,
        selector=Selector(caller_kind=type(node)),
    )
    dispatch_result = CallReceipt.merge_results(*receipts)
    layers.extend(_coerce_ns_layers(dispatch_result, source="gather_ns handler"))

    nested_overlay = _merge_nested_layers(layers)
    if nested_overlay:
        layers = [nested_overlay, *layers]

    return ChainMap(*layers) if layers else ChainMap()


# ---------------------------------------------------------------------------
# Provisioning hook (separate — different call signature)
# ---------------------------------------------------------------------------

def on_resolve(func=None, **kwargs):
    """Register a handler for requirement resolution."""
    if func is None:
        return lambda f: dispatch.register(func=f, task="resolve_req", **kwargs)
    return dispatch.register(func=func, task="resolve_req", **kwargs)


def do_resolve(requirement: Requirement, *, offers: Iterable[ProvisionOffer], ctx):
    """Execute ``resolve_req`` handlers and flatten validated offer overrides.

    Contract:
    - handler returns ``None`` to keep existing offers unchanged
    - handler returns ``Iterable[ProvisionOffer]`` to contribute overrides
    """
    _validate_dispatch_ctx(ctx)
    receipts = dispatch.execute_all(
        task="resolve_req",
        call_kwargs={"caller": requirement, "offers": offers},
        ctx=ctx,
    )
    results = CallReceipt.gather_results(*receipts)
    if not results:
        return None

    from .provision import ProvisionOffer as _ProvisionOffer

    flattened: list[_ProvisionOffer] = []
    for result in results:
        if isinstance(result, (str, bytes, dict)) or not isinstance(result, IterableABC):
            raise TypeError(
                "resolve_req handlers must return None or Iterable[ProvisionOffer]"
            )
        for offer in result:
            if not isinstance(offer, _ProvisionOffer):
                raise TypeError(
                    "resolve_req handlers must return iterables containing only ProvisionOffer"
                )
            flattened.append(offer)
    return flattened


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "dispatch",
    # phase decos and invocation
    "on_validate", "do_validate",
    "on_provision", "do_provision",
    "on_prereqs", "do_prereqs",
    "on_update", "do_update",
    "on_journal", "do_journal",
    "on_finalize", "do_finalize",
    "on_postreqs", "do_postreqs",
    # helper decos and invocation
    "on_gather_ns", "do_gather_ns",
    "on_resolve", "do_resolve",
]
