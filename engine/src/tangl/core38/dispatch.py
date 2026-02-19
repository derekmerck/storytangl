# tangl/core/dispatch.py
# language=markdown
"""
Default global dispatch registry and explicit hook pairs for core38 lifecycle events.

Hook pairs are exposed as explicit decorators and runners:

- creation:
  - ``on_create`` / ``do_create`` (pre-structuring, ``data -> data``)
  - ``on_init`` / ``do_init`` (post-init, ``caller -> None``)
- registry indexing:
  - ``on_add_item`` / ``do_add_item`` (``registry, item -> item``)
  - ``on_get_item`` / ``do_get_item`` (``registry, item -> item``)
  - ``on_remove_item`` / ``do_remove_item`` (``registry, item -> None``)
- graph relationships:
  - ``on_link`` / ``do_link`` (``caller, node -> None``)
  - ``on_unlink`` / ``do_unlink`` (``caller, node -> None``)

Context contract
----------------
Dispatch chaining is driven by the runtime context protocol used by
:class:`tangl.core38.behavior.BehaviorRegistry`:

- ``ctx.get_registries()`` contributes extra registries by layer.
- ``ctx.get_inline_behaviors()`` contributes one-off callables.

Callers normally pass ``_ctx`` to hook-aware APIs (for example ``Entity(..., _ctx=ctx)``,
``Entity.structure(..., _ctx=ctx)``, ``Registry.add(..., _ctx=ctx)``), or rely on ambient
context via :func:`tangl.core38.ctx.using_ctx`.

Aggregation contracts
---------------------

- ``do_create`` folds hook results with :meth:`CallReceipt.merge_results`.
- ``do_add_item`` and ``do_get_item`` use :meth:`CallReceipt.last_result`.
- ``do_init``, ``do_remove_item``, ``do_link``, and ``do_unlink`` force receipt
  evaluation with :meth:`CallReceipt.gather_results`.

Example:
    >>> assert Entity(label="bar").label == "bar"
    >>> _ = on_init(func=lambda *, caller, ctx = None, **kwargs: setattr(caller, "label", "foo"))
    >>> item = Entity(
    ...     label="bar",
    ...     _ctx=SimpleNamespace(
    ...         get_registries=lambda: [],
    ...         get_inline_behaviors=lambda: [],
    ...     ),
    ... )  # calls global dispatch by default
    >>> assert item.label == "foo"
    >>> q = BehaviorRegistry()
    >>> _ = q.register(task="init", dispatch_layer=DispatchLayer.APPLICATION,
    ...                func=lambda *, caller, ctx = None, **kwargs: setattr(caller, "label", "baz"))
    >>> item = Entity(
    ...     label="bar",
    ...     _ctx=SimpleNamespace(
    ...         get_registries=lambda: [q],
    ...         get_inline_behaviors=lambda: [],
    ...     ),
    ... )
    >>> assert item.label == "baz"
    >>> dispatch.clear()  # always clean up global registries after using


## Dispatch Layer Mapping

| Layer       | Package   | Registry            | Typical Tasks                   |
|-------------|-----------|---------------------|---------------------------------|
| GLOBAL      | core      | `core.dispatch`     | Auditing, logging               |
| SYSTEM      | vm        | `vm.dispatch`       | Phase handlers, provisioning    |
| SYSTEM      | service   | `service.dispatch`  | Api, persistence                |
| APPLICATION | story     | `story.dispatch`    | Content rendering, domain rules |
| APPLICATION | mechanics | `story.dispatch`    | Extend story semantics          |
| APPLICATION | discourse | `story.dispatch`    | Extend story prose models       |
| APPLICATION | media     | `story.dispatch`    | Extend story with media         |
| AUTHOR      | world     | `world.dispatch`    | World-specific mechanics        |
| LOCAL       | vm.frame  | `vm.frame.dispatch` | One-off handlers                |

"""
from types import SimpleNamespace
from copy import deepcopy

from tangl.type_hints import UnstructuredData
from .entity import Entity
from .selector import Selector
from .registry import Registry
from .behavior import RuntimeCtx, BehaviorRegistry, DispatchLayer, CallReceipt
from .graph import GraphItem, Node

dispatch = BehaviorRegistry(label="global_dispatch", default_dispatch_layer=DispatchLayer.GLOBAL)

# Creation hooks
# --------------

def on_init(func, **kwargs):
    """Register an ``init`` hook on the global dispatch registry."""
    return dispatch.register(func=func, task="init", **kwargs)

def do_init(*, caller: Entity, ctx: RuntimeCtx):
    """Run ``init`` hooks for a newly constructed caller."""
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'caller': caller},
        selector=Selector(caller_kind=type(caller)),  # only match caller-compatible behaviors
        task="init",
    )
    CallReceipt.gather_results(*receipts)  # force results to evaluate

def on_create(func, **kwargs):
    """Register a ``create`` hook on the global dispatch registry."""
    return dispatch.register(func=func, task="create", **kwargs)

def do_create(*, data: UnstructuredData, ctx: RuntimeCtx):
    """Run ``create`` hooks and merge returned mapping updates into structuring input."""
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'data': data},
        task="create",
    )
    update = CallReceipt.merge_results(*receipts)
    if update:
        data = deepcopy(data) | update
    return data

# Indexing hooks
# --------------

def on_add_item(func, **kwargs):
    """Register an ``add_item`` hook for registry insertion."""
    return dispatch.register(func=func, task="add_item", **kwargs)

def do_add_item(registry: Registry, item: Entity, ctx: RuntimeCtx):
    """Run ``add_item`` hooks and return the final inserted entity.

    The last non-``None`` receipt result wins. If no hook returns a replacement,
    the original ``item`` is returned.
    """
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task="add_item",
    )
    result = CallReceipt.last_result(*receipts)
    return result if result is not None else item

def on_get_item(func, **kwargs):
    """Register a ``get_item`` hook for registry lookup interception."""
    return dispatch.register(func=func, task="get_item", **kwargs)

def do_get_item(registry: Registry, item: Entity, ctx: RuntimeCtx) -> Entity:
    """Run ``get_item`` hooks and return the final fetched entity."""
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task="get_item",
    )
    result = CallReceipt.last_result(*receipts)
    return result if result is not None else item

def on_remove_item(func, **kwargs):
    """Register a ``remove_item`` hook for post-removal inspection."""
    return dispatch.register(func=func, task="remove_item", **kwargs)

def do_remove_item(registry: Registry, item: Entity, ctx: RuntimeCtx):
    """Run ``remove_item`` hooks after registry removal."""
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task="remove_item",
    )
    CallReceipt.gather_results(*receipts)  # force receipt evaluation

# Graph hooks
# --------------

def on_link(func, **kwargs):
    """Register a ``link`` hook for graph relationships."""
    return dispatch.register(func=func, task="link", **kwargs)

def do_link(caller: GraphItem, node: Node, ctx: RuntimeCtx):
    """Run ``link`` hooks for edge endpoint or group membership linking."""
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'caller': caller, 'node': node},
        task="link",
    )
    CallReceipt.gather_results(*receipts)

def on_unlink(func, **kwargs):
    """Register an ``unlink`` hook for graph relationship teardown."""
    return dispatch.register(func=func, task="unlink", **kwargs)

def do_unlink(caller: GraphItem, node: Node, ctx: RuntimeCtx):
    """Run ``unlink`` hooks after edge endpoint or group membership unlinking."""
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'caller': caller, 'node': node},
        task="unlink",
    )
    CallReceipt.gather_results(*receipts)
