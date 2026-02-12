from typing import Iterable

from tangl.core38 import BehaviorRegistry, DispatchLayer
from .provision import Requirement, ProvisionOffer

dispatch = BehaviorRegistry(label="vm_dispatch", default_dispatch_layer=DispatchLayer.SYSTEM)

def on_resolve(func, **kwargs):
    return dispatch.register(func=func, task="resolve_requirement", **kwargs)

def do_resolve(*, requirement: Requirement, offers: Iterable[ProvisionOffer], ctx): ...
