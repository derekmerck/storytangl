from __future__ import annotations
from functools import partial

from tangl.vm.resolution_phase import ResolutionPhase as P
from .vm_dispatch import vm_dispatch

on_update = partial(vm_dispatch.register, task=P.UPDATE)
on_finalize = partial(vm_dispatch.register, task=P.FINALIZE)


@on_update()
def update_noop(*args, **kwargs):
    pass

@on_finalize()
def finalize_noop(*args, **kwargs):
    # collapse-to-patch can go here later
    pass
