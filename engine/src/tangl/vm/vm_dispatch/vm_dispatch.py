# /tangl/vm/vm_dispatch/vm_dispatch.py
from functools import partial

from tangl.core.dispatch import HandlerLayer as L
from tangl.core.dispatch.core_dispatch import LayeredDispatch
from tangl.vm.frame import ResolutionPhase as P

vm_dispatch = LayeredDispatch(label="vm.dispatch", handler_layer=L.SYSTEM)

