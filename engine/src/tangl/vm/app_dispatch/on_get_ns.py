import logging

from tangl.core import BehaviorRegistry
from tangl.core.dispatch.behavior import HandlerLayer

logger = logging.getLogger(__name__)

on_get_ns = BehaviorRegistry(
    label="on_get_ns",
    task="get_ns",
    handler_layer=HandlerLayer.APPLICATION
)

def _contribute_locals_to_ns(caller, *args, ctx=None, **params):
    if hasattr(caller, "locals"):
        return caller.locals

on_get_ns.add_behavior(_contribute_locals_to_ns)
