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
from typing import Any, Callable, Iterable, Optional, TYPE_CHECKING

from tangl.core38 import BehaviorRegistry, CallReceipt, DispatchLayer, Node, Record

if TYPE_CHECKING:
    from .provision import Requirement, ProvisionOffer
    from .traversable import TraversableNode, TraversableEdge, AnyTraversableEdge

    Fragment = Record
    Patch = Record

logger = logging.getLogger(__name__)


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


def _make_do_hook(task: str, aggregator: Callable) -> Callable:
    """Create an execution function for a phase task."""
    def do_hook(caller, *, ctx, **kwargs):
        registries = _assemble_registries(ctx)
        receipts = BehaviorRegistry.chain_execute(
            *registries,
            task=task,
            call_kwargs={"caller": caller, **kwargs},
            ctx=ctx,
        )
        return aggregator(*receipts)
    do_hook.__name__ = f"do_{task}"
    do_hook.__doc__ = f"Execute all ``{task}`` handlers and aggregate results."
    return do_hook


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

# Execution hooks
do_validate  = _make_do_hook("validate_edge",   CallReceipt.all_true)
do_provision = _make_do_hook("provision_node",   CallReceipt.gather_results)
do_prereqs   = _make_do_hook("get_prereqs",      CallReceipt.first_result)
do_update    = _make_do_hook("apply_update",     CallReceipt.gather_results)
do_journal   = _make_do_hook("render_journal",   CallReceipt.last_result)
do_finalize  = _make_do_hook("finalize_step",    CallReceipt.last_result)
do_postreqs  = _make_do_hook("get_postreqs",     CallReceipt.first_result)


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
    """Execute all ``resolve_req`` handlers and gather results."""
    registries = _assemble_registries(ctx)
    receipts = BehaviorRegistry.chain_execute(
        *registries,
        task="resolve_req",
        call_kwargs={"caller": requirement, "offers": offers},
        ctx=ctx,
    )
    return CallReceipt.gather_results(*receipts)


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
