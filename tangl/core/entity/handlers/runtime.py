from __future__ import annotations
from typing import Any
import logging

from tangl.type_hints import Expr
from tangl.core.graph import Node
from tangl.core.task_handler import TaskPipeline, PipelineStrategy
from .has_context import HasContext

logger = logging.getLogger(__name__)

def setup_on_check_conditions_pipeline() -> TaskPipeline[HasConditions, bool]:
    if pipeline := TaskPipeline.get_instance(label="on_check_conditions"):
        pass
    else:
        pipeline = TaskPipeline(label="on_check_conditions", pipeline_strategy=PipelineStrategy.ALL)

    return pipeline

# todo: can't invoke pipelines directly b/c they requires context
on_check_conditions = setup_on_check_conditions_pipeline()


class HasConditions(HasContext):

    conditions: list[Expr] = None

    @classmethod
    def eval_str(cls, s: str, **context) -> Any:
        if not s:
            return
        result = eval(s, {}, context)
        logger.debug(f"eval {s} with {context} = {result}")
        return result

    @classmethod
    def all_conditions_true(cls, conditions: list[Expr], context: dict = None) -> bool:
        return all([ cls.eval_str( c, **context ) for c in conditions ])

    @on_check_conditions.register()
    def _check_my_conditions(self, **context) -> bool:
        return self.all_conditions_true(self.conditions, context)

    @on_check_conditions.register(caller_cls=Node)
    def _check_my_conditions(self, **context) -> bool:
        if self.parent and isinstance(self.parent, HasConditions):
            return on_check_conditions.execute(self.parent, **context)

    def check_conditions(self, **context) -> bool:
        context = context or self.gather_context()
        return on_check_conditions.execute(self, **context)

def setup_on_apply_effects_pipeline() -> TaskPipeline[HasEffects, Any]:
    if pipeline := TaskPipeline.get_instance(label="on_apply_effects"):
        pass
    else:
        pipeline = TaskPipeline(label="on_apply_effects", pipeline_strategy=PipelineStrategy.GATHER)

    return pipeline

on_apply_effects = setup_on_apply_effects_pipeline()


class HasEffects(HasContext):

    effects: list[Expr] = None

    @classmethod
    def exec_str(cls, s: str, **context):
        if not s:
            return
        logger.debug(f"exec {s} with {context}")
        result = eval(s, {}, **context)
        return result

    @classmethod
    def apply_all_effects(cls, effects: list[Expr], context: dict = None):
        for e in effects:
            cls.exec_str(e, **context)

    @on_check_conditions.register()
    def _apply_my_effects(self, **context):
        self.apply_all_effects(self.effects, context)

    def apply_effects(self, **context) -> bool:
        context = context or self.gather_context()
        return on_apply_effects.execute(self, **context)
