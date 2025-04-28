from __future__ import annotations
from typing import Any
import logging

import pytest

from ..handler_pipeline import HandlerPipeline, PipelineStrategy
from ..graph import Edge
from .has_context import HasContext
from .has_conditions import on_check_conditions, HasConditions

logger = logging.getLogger(__name__)

on_avail = HandlerPipeline[HasContext, bool](label="on_avail", pipeline_strategy=PipelineStrategy.ALL)
"""
The global pipeline for testing availability. Handlers for availability tests
should decorate methods with ``@on_avail.register(...)``.
"""

class Available(HasContext):

    locked: bool = False
    forced: bool = False

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def force(self):
        self.forced = True
        self.dirty = True

    @on_avail.register()
    def _check_locked(self, **context) -> bool:
        return not self.locked or self.forced

    @on_avail.register(caller_cls=HasConditions)
    def _check_conditions(self, **context) -> bool:
        return on_check_conditions.execute(**context)

    @on_avail.register(caller_cls=Edge)
    def _check_successor_avail(self, **context) -> bool:
        if self.successor is None:
            return False
        return self.successor.avail(**context)
        # todo: do we want to check this in the edge's context,
        #       or re-evaluate the successor's context?

    def avail(self, **context) -> bool:
        context = context or self.gather_context()
        return on_avail.execute(self, **context)
