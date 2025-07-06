from __future__ import annotations
from typing import TYPE_CHECKING

from .phase import Phase
from .io import apply_patch

if TYPE_CHECKING:
    from .behaviors.behavior_registry import BehaviorRegistry

def step(ir, registry: BehaviorRegistry):
    patches = []
    for ph in Phase:
        behaviour = registry.get_best(ph)
        ir, delta = behaviour(ir)
        patches.extend(delta)
    # apply patches to IR (optional in S-1 if behaviors already return new IR)
    for p in patches:
        ir = apply_patch(ir, p)
    return ir, patches