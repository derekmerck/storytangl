"""
Default global-layer behavior registry ('core.dispatch') and decorators ('on_task') and callbacks ('do_task') for global layer hooks:

- creation:
  - create (pre-structuring, data -> data)
  - init (post-init, item -> None)
- indexing:
  - add item  (registry add, reg, item -> None)
  - get item  (registry get, reg, key -> item)
  - remove item (registry remove, reg, key -> None)

Passing a ctx kwarg into any hooked method triggers any registered hooks in the responsible
dispatch or any dispatch provided by ctx.

See `Entity.__init__()`, `Registry.add_item()`, etc. for injection examples.

See `vm.dispatch`, `story.dispatch`, `service.dispatch`, etc. for examples of other dispatch layers and pre-defined hook points.

Example:
    >>> Entity(label="bar")
    <Entity:bar>
    >>> _ = on_init(func=lambda *, caller, ctx = None, **kwargs: setattr(caller, "label", "foo"))
    >>> Entity(label="bar", ctx=SimpleNamespace(get_registries=lambda: []))  # calls global dispatch by default
    <Entity:foo>
    >>> q = BehaviorRegistry()
    >>> _ = q.register(task="init", dispatch_layer=DispatchLayer.APPLICATION,
    ...                func=lambda *, caller, ctx = None, **kwargs: setattr(caller, "label", "baz"))
    >>> Entity(label="bar", ctx=SimpleNamespace(get_registries=lambda: [q]))
    <Entity:baz>
    >>> dispatch.clear()  # always clean up global registries after using
"""
from types import SimpleNamespace
from copy import deepcopy

from tangl.type_hints import UnstructuredData
from .entity import Entity
from .selector import Selector
from .registry import Registry
from .behavior import RuntimeCtx, BehaviorRegistry, DispatchLayer, CallReceipt

dispatch = BehaviorRegistry(default_dispatch_layer=DispatchLayer.GLOBAL)

# Creation hooks
# --------------

def on_init(func):
    # registration deco
    return dispatch.register(func=func, task="init")

def do_init(*, caller: Entity, ctx: RuntimeCtx):
    # chance to validate in-place
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(
        *registries,
        ctx=ctx,
        call_kwargs={'caller': caller},
        selector = Selector(has_kind=type(caller)), # only want to match for caller type
        task = "init"
    )
    CallReceipt.gather_results(*receipts)  # force results to evaluate

def on_create(func):
    return dispatch.register(func=func, task="create")

def do_create(*, data: UnstructuredData, ctx: RuntimeCtx):
    """Chance to fold in updates to unstructured data/inst kwargs, including the kind-hint"""
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(
        *registries,
        ctx=ctx,
        call_kwargs={'data': data},
        task = "create"
    )
    update = CallReceipt.merge_results(*receipts)
    if update:
        data = deepcopy(data) | update
    return data

# Indexing hooks
# --------------

def on_add_item(func):
    return dispatch.register(func=func, task="add_item")

def do_add_item(registry: Registry, item: Entity, ctx: RuntimeCtx):
    # chance to modify the item before inserting it
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(
        *registries,
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task = "add_item"
    )
    return CallReceipt.last_result(*receipts) or item

def on_get_item(func):
    return dispatch.register(func=func, task="get_item")

def do_get_item(registry: Registry, item: Entity, ctx: RuntimeCtx) -> Entity:
    # chance to modify or update the requested object before returning it
    # chance to modify the item before inserting it
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(
        *registries,
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task = "get_item"
    )
    return CallReceipt.last_result(*receipts) or item


def on_remove_item(func):
    return dispatch.register(func=func, task="remove_item")

def do_remove_item(registry: Registry, item: Entity, ctx: RuntimeCtx):
    # chance to audit the requested object before discarding it
    # chance to modify the item before inserting it
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(
        *registries,
        ctx=ctx,
        call_kwargs={'registry': registry, 'item': item},
        task = "add_item"
    )
    CallReceipt.gather_results(*receipts) or item

