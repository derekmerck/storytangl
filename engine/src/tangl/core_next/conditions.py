from pydantic import Field

from .task_handler import TaskRegistry as HandlerPipeline
from .context import ContextView, ContextBuilder
from .node import Node
from .base import Entity

class ConditionChecker:
    gather_pipeline = HandlerPipeline(label="on_gather_conditions")

    @classmethod
    def eval_expr(cls, expr, ctx):
        return eval(expr, {}, ctx)

    @classmethod
    def check(cls, entity: Entity, ctx: ContextView):
        conditions = cls.gather_pipeline.execute_all(entity=entity, ctx=ctx)
        conditions = [ c for c_list in conditions for c in c_list ]  # flatten list of lists
        return all(cls.eval_expr(c, ctx) for c in conditions)


class HasConditions(Node):

    conditions: list[str] = Field(default_factory=list)

    @ConditionChecker.gather_pipeline.register()
    def _my_conditions(self) -> list[str]:
        return self.conditions

