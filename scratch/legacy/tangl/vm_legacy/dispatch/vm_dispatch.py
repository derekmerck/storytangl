# /tangl/vm/vm_dispatch/vm_dispatch.py
from tangl.core.behavior import HandlerLayer as L
from tangl.core.dispatch.core_dispatch import LayeredDispatch

vm_dispatch = LayeredDispatch(label="vm.dispatch", handler_layer=L.SYSTEM)
