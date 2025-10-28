# tangl/core/dispatch/__init__.py
from .call_receipt import CallReceipt
from tangl.utils.func_info import HandlerFunc  # Convenience surface for protocol
from .behavior import Behavior, HandlerPriority, HandlerLayer
from .behavior_registry import BehaviorRegistry
from .has_behaviors import HasBehaviors, HasLocalBehaviors

DEFAULT_HANDLERS = BehaviorRegistry(label='default_handlers')

