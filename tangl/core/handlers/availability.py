from __future__ import annotations
import logging

from .task_handler import TaskPipeline, PipelineStrategy
from .has_context import HasContext
from .runtime import on_check_conditions, HasConditions

logger = logging.getLogger(__name__)

def setup_on_avail_pipeline() -> TaskPipeline[Available, bool]:
    if pipeline := TaskPipeline.get_instance(label="on_avail"):
        pass
    else:
        pipeline = TaskPipeline(label="on_avail", pipeline_strategy=PipelineStrategy.ALL)

    return pipeline

# todo: can't invoke this directly b/c it requires context
on_avail = setup_on_avail_pipeline()

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

    def avail(self, **context) -> bool:
        context = context or self.gather_context()
        return on_avail.execute(self, **context)
