# tangl/core/dispatch.py
# language=markdown
"""
Default global-layer behavior registry ('core.dispatch') and decorators ('on_task') and callbacks ('do_task') for global layer hooks:

- creation:
  - create (pre-structuring, data -> data)
  - init (post-init, item -> None)
- indexing:
  - add item  (registry add, reg, item -> None)
  - get item  (registry get, reg, key -> item)
  - remove item (registry remove, reg, key -> None)
- relationships:
  - link node on edge or group
  - unlink node from edge or group

Passing a _ctx kwarg into any hooked method triggers any registered hooks in the responsible
dispatch or any dispatch provided by ctx.

Alternatively, using an ambient "ctx.using_ctx()" context manager will passively provide _ctx signals to any method expecting it.

See `Entity.__init__()`, `Registry.add_item()`, etc. for injection examples.

See `vm.dispatch`, `story.dispatch`, `service.dispatch`, etc. for examples of other dispatch layers and pre-defined hook points.

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
    # restrict caller type to exact?
    # registration deco
    return dispatch.register(func=func, task="init", **kwargs)

def do_init(*, caller: Entity, ctx: RuntimeCtx):
    # chance to validate in-place
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'caller': caller},
        selector=Selector(caller_kind=type(caller)),  # only match caller-compatible behaviors
        task="init",
    )
    CallReceipt.gather_results(*receipts)  # force results to evaluate

def on_create(func, **kwargs):
    return dispatch.register(func=func, task="create", **kwargs)

def do_create(*, data: UnstructuredData, ctx: RuntimeCtx):
    """Chance to fold in updates to unstructured data/inst kwargs, including the kind-hint"""
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
    return dispatch.register(func=func, task="add_item", **kwargs)

def do_add_item(registry: Registry, item: Entity, ctx: RuntimeCtx):
    # chance to audit or modify the item _before_ inserting it
    # todo: do we want to allow this to be mutated or, or is it read only for
    #       inspection/audit like remove?  can modify on `get` if we need to
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task="add_item",
    )
    result = CallReceipt.last_result(*receipts)
    return result if result is not None else item

def on_get_item(func, **kwargs):
    return dispatch.register(func=func, task="get_item", **kwargs)

def do_get_item(registry: Registry, item: Entity, ctx: RuntimeCtx) -> Entity:
    # chance to modify or update the requested object before returning it
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task="get_item",
    )
    result = CallReceipt.last_result(*receipts)
    return result if result is not None else item

def on_remove_item(func, **kwargs):
    return dispatch.register(func=func, task="remove_item", **kwargs)

def do_remove_item(registry: Registry, item: Entity, ctx: RuntimeCtx):
    # chance to audit the requested object after removal but before discarding it
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task="remove_item",
    )
    CallReceipt.gather_results(*receipts)  # force receipt evaluation

# Graph hooks
# --------------

def on_link(func, **kwargs):
    return dispatch.register(func=func, task="link", **kwargs)

def do_link(caller: GraphItem, node: Node, ctx: RuntimeCtx):
    # audit _before_ linking
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'caller': caller, 'node': node},
        task="link",
    )
    CallReceipt.gather_results(*receipts)

def on_unlink(func, **kwargs):
    return dispatch.register(func=func, task="unlink", **kwargs)

def do_unlink(caller: GraphItem, node: Node, ctx: RuntimeCtx):
    # audit _after_ unlinking (undiscarded, remains in graph)
    receipts = dispatch.execute_all(
        ctx=ctx,
        call_kwargs={'caller': caller, 'node': node},
        task="unlink",
    )
    CallReceipt.gather_results(*receipts)
