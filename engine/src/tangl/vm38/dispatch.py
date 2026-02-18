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

The ``on_gather_ns`` / ``do_gather_ns`` hook is separate because it walks the ancestor
chain (scoped dispatch semantic) rather than firing once at the cursor.

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
from collections.abc import Iterable as IterableABC
from typing import Any, Callable, Iterable, Optional, TYPE_CHECKING, Protocol, runtime_checkable

from tangl.core38 import BehaviorRegistry, CallReceipt, DispatchLayer, Node, Record

if TYPE_CHECKING:
    from .provision import Requirement, ProvisionOffer
    from .traversable import TraversableNode, TraversableEdge, AnyTraversableEdge

    Fragment = Record
    Patch = Record

logger = logging.getLogger(__name__)

Fragment = Record
Patch = Record


@runtime_checkable
class VmDispatchCtx(Protocol):
    """Minimal context contract required by vm38 dispatch hooks."""

    def get_registries(self) -> list[BehaviorRegistry]: ...
    def get_inline_behaviors(self) -> Iterable[Callable | Any]: ...


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

def _assemble_registries(ctx) -> list[BehaviorRegistry]:
    """Collect registries from ctx and ensure vm_dispatch is included."""
    if not isinstance(ctx, VmDispatchCtx):
        raise TypeError(
            "Dispatch context must provide get_registries() and get_inline_behaviors()"
        )
    registries = list((ctx.get_registries() if ctx else None) or [])
    if dispatch not in registries:
        registries.append(dispatch)
    return registries


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
    registries = _assemble_registries(ctx)
    receipts = BehaviorRegistry.chain_execute(
        *registries,
        task=task,
        call_kwargs={"caller": caller, **kwargs},
        ctx=ctx,
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
    result = CallReceipt.last_result(*_run_task("render_journal", caller=caller, ctx=ctx, **kwargs))
    return _assert_journal_result(result)


def do_finalize(caller, *, ctx, **kwargs):
    result = CallReceipt.last_result(*_run_task("finalize_step", caller=caller, ctx=ctx, **kwargs))
    return _assert_patch_result(result)


def do_postreqs(caller, *, ctx, **kwargs):
    result = CallReceipt.first_result(*_run_task("get_postreqs", caller=caller, ctx=ctx, **kwargs))
    return _assert_redirect_result(result, task="get_postreqs")


# ---------------------------------------------------------------------------
# Namespace gathering hook — scoped dispatch semantic
# ---------------------------------------------------------------------------

on_gather_ns = _make_on_hook("gather_ns")
"""Register a namespace contributor.

Namespace handlers receive ``caller=<ancestor_node>`` and return a dict of
symbols to contribute.  They are fired once per ancestor in the hierarchy
walk (from root to node), so a handler registered for a specific caller kind
only fires when an ancestor of that kind is encountered.

Examples::

    @on_gather_ns
    def contribute_locals(*, caller, ctx, **kw):
        if hasattr(caller, 'locals') and caller.locals:
            return caller.locals

    @on_gather_ns
    def contribute_satisfied_deps(*, caller, ctx, **kw):
        from tangl.vm38.provision import Dependency, Affordance
        from tangl.core38 import Selector
        reqs = caller.edges_out(Selector(has_kind=(Dependency, Affordance)))
        return {r.get_label(): r.successor for r in reqs if r.satisfied}
"""


def do_gather_ns(node: Node, *, ctx) -> ChainMap[str, Any]:
    """Build a scoped namespace by walking the ancestor chain.

    Walks ``node.ancestors`` (which includes ``node`` itself) from root to
    node.  At each ancestor, fires all ``gather_ns`` handlers with
    ``caller=ancestor``.  Results are merged into a :class:`ChainMap` where
    closer scope (node) overrides more distant scope (root).

    This implements the *scoped dispatch* semantic from legacy: the same
    handlers fire at each level of the hierarchy, receiving different callers.
    A handler that contributes ``.locals`` fires once per ancestor that has
    locals; a handler that contributes satisfied deps fires once per ancestor
    that has deps.

    Parameters
    ----------
    node
        The node to build namespace for (usually the cursor).
    ctx
        Dispatch context providing registries.

    Returns
    -------
    ChainMap[str, Any]
        Namespace with closest scope first.  Use ``dict(result)`` for a
        flat dict if ChainMap semantics aren't needed.

    Notes
    -----
    Handlers must NOT call ``ctx.get_ns()`` for the same node — that would
    cause infinite recursion through the cache.  Use priority ordering
    (EARLY/LATE) if a handler needs access to other namespace contributions.
    """
    registries = _assemble_registries(ctx)

    # Walk from node to root: [node, parent, grandparent, ..., root]
    ancestors = list(node.ancestors) if hasattr(node, "ancestors") else [node]

    # Fire handlers at each ancestor level, collect per-level dicts
    layers: list[dict[str, Any]] = []
    for ancestor in ancestors:
        receipts = BehaviorRegistry.chain_execute(
            *registries,
            task="gather_ns",
            call_kwargs={"caller": ancestor},
            ctx=ctx,
        )
        layer = CallReceipt.merge_results(*receipts)
        if layer:
            layers.append(layer if isinstance(layer, dict) else dict(layer))

    # ChainMap: first map wins on lookup → closest scope overrides
    # ancestors list is [node, parent, ..., root], which is already closest-first
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
    registries = _assemble_registries(ctx)
    receipts = BehaviorRegistry.chain_execute(
        *registries,
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
