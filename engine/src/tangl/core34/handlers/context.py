from collections import ChainMap
import logging
from pydantic import Field

from .base import HasHandlers, handler
from .enums import ServiceKind

logger = logging.getLogger(__name__)

class HasContext(HasHandlers):

    locals: dict = Field(default_factory=dict)

    @handler(ServiceKind.CONTEXT, priority=1)
    def _provide_locals(self, _):
        return self.locals

    @staticmethod
    def context_handler(priority=10, caller_criteria=None):
        return handler(ServiceKind.CONTEXT, priority=priority, caller_criteria=caller_criteria)

    @classmethod
    def gather_context(cls, caller, *objects):
        logger.debug("gathering context")
        maps = []
        for h in cls.gather_handlers(ServiceKind.CONTEXT, caller, *objects, ctx=None):
            logger.debug(f"Calling: {h!r}")
            maps.append(h.func(caller, None))
        # Include self-reference in context
        return ChainMap({'caller': caller}, *maps)
