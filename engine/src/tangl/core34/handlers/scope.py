from pydantic import PrivateAttr

from ..entity import Singleton
from .enums import ServiceKind
from .base import HasHandlers, HandlerRegistry

class Scope(HasHandlers, Singleton):
    # Singleton collection of handlers that accepts instance registrations

    _instance_handlers: HandlerRegistry = PrivateAttr(default_factory=HandlerRegistry)

    def clear_instance_handlers(self):
        return self._instance_handlers.clear()

    def register_instance_handler(self, service: ServiceKind, priority: int = 0, caller_criteria=None):
        return self._handler_registry.register_handler(
            service=service,
            priority=priority,
            caller_criteria=caller_criteria,
            owner_cls=self.__class__,
            is_instance_handler=True,
        )
