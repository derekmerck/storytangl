from __future__ import annotations
from typing import Iterable, Optional, TYPE_CHECKING

from tangl.core38 import BehaviorRegistry, DispatchLayer, CallReceipt, Record

if TYPE_CHECKING:
    from .provision import Requirement, ProvisionOffer
    from .traversable import TraversableNode, TraversableEdge
    Fragment = Record
    Patch = Record

dispatch = BehaviorRegistry(label="vm_dispatch", default_dispatch_layer=DispatchLayer.SYSTEM)


# this is a LOT of api boilerplate
# all the 'do' hooks should look like this -- can we create them programmatically?
# the registries business can be done inside chain-execute if it gets a context
# converting named args to caller, etc. and aggregation is maybe a lookup table?

# Provisioning Hooks
# ------------------

def on_resolve(func, **kwargs):
    return dispatch.register(func=func, task="resolve_req", **kwargs)

def do_resolve(requirement: Requirement, *, offers: Iterable[ProvisionOffer], ctx):
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="resolve_req", ctx=ctx, call_kwargs={'caller': requirement, 'offers': offers})
    return CallReceipt.gather_results(*receipts)

# Phase Bus Hooks
# ------------------

def on_validate(func, **kwargs):
    return dispatch.register(func=func, task="validate_edge", **kwargs)

def do_validate(edge: TraversableEdge, *, ctx) -> bool:
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="validate_edge", call_kwargs={'caller': edge}, ctx=ctx)
    return CallReceipt.all_true(*receipts)

def on_provision(func, **kwargs):
    return dispatch.register(func=func, task="provision_node", **kwargs)

def do_provision(node: TraversableNode, *, ctx, force=False):
    # if -force- we need to fill any hard deps with a placeholder of the correct kind at least
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="provision_node", call_kwargs={'caller': node}, ctx=ctx)
    return CallReceipt.gather_results(*receipts)

def on_prereqs(func, **kwargs):
    return dispatch.register(func=func, task="get_prereqs", **kwargs)

def do_prereqs(node: TraversableNode, *, ctx) -> Optional[TraversableEdge]:
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="get_prereqs", call_kwargs={'caller': node}, ctx=ctx)
    # ensure this is an edge with return_phase = PREREQS if not None
    return CallReceipt.first_result(*receipts)

def on_update(func, **kwargs):
    return dispatch.register(func=func, task="apply_update", **kwargs)

def do_update(node: TraversableNode, *, ctx):
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="apply_update", call_kwargs={'caller': node}, ctx=ctx)
    return CallReceipt.gather_results(*receipts)

def on_journal(func, **kwargs):
    return dispatch.register(func=func, task="render_journal", **kwargs)

def do_journal(node: TraversableNode, *, ctx) -> Iterable[Fragment]:
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="render_journal", call_kwargs={'caller': node}, ctx=ctx)
    # Uses a LAST aggregator
    return CallReceipt.last_result(*receipts)

def on_finalize(func, **kwargs):
    return dispatch.register(func=func, task="finalize_step", **kwargs)

def do_finalize(node: TraversableNode, *, ctx) -> Optional[Patch]:
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="finalize_step", call_kwargs={'caller': node}, ctx=ctx)
    return CallReceipt.last_result(*receipts)

def on_postreqs(func, **kwargs):
    return dispatch.register(func=func, task="get_postreqs", **kwargs)

def do_postreqs(node: TraversableNode, *, ctx) -> Optional[TraversableEdge]:
    registries = ctx.get_registries() or []
    if dispatch not in registries:
        registries.append(dispatch)
    receipts = dispatch.chain_execute(*registries, task="get_postreqs", call_kwargs={'caller': node}, ctx=ctx)
    # ensure this is an edge with return_phase = POSTREQS if not None
    return CallReceipt.first_result(*receipts)


