from __future__ import annotations
from typing import TYPE_CHECKING

from .phase import Phase
from .io import apply_patch

from .context import Context
if TYPE_CHECKING:
    from .behaviors.behavior_registry import BehaviorRegistry

def step(ir, behaviors: BehaviorRegistry):

    ctx = Context(
        shape=ir.shape,
        stack=ir.layer_stack,       # LayerStack instance
        state=ir.state,
        tick = ir.tick + 1,
    )

    patches = []
    for phase in Phase:
        fn = behaviors.get_best(phase)
        ctx, delta = fn(ctx)
        if not isinstance(delta, list):
            patches.append(delta)
        else:
            patches.extend(delta)

    # fold patches back into the IR
    new_ir = ir
    for p in patches:
        new_ir = apply_patch(new_ir, p)
    # sync global state & tick from ctx
    new_ir = new_ir.evolve(state=ctx.state, tick=ctx.tick)
    return new_ir, patches