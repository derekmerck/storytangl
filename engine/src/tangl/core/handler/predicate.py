import logging

from pydantic import field_validator, Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.dispatch import HandlerRegistry
from .context import HasContext
from .runtime_object import RuntimeObject

logger = logging.getLogger(__name__)

class Predicate(RuntimeObject):

    @classmethod
    def eval_structured_expr(cls, expr: StringMap, *, ctx: StringMap = None):
        raise NotImplementedError("Structured predicate evaluation not yet implemented")

    def evaluate(self, entity: Entity, *, ctx: StringMap = None):
        if self.structured_expr is not None:
            return self.eval_structured_expr(self.structured_expr, ctx=ctx)
        elif self.raw_expr is not None:
            return self.eval_raw_expr(self.raw_expr, ctx=ctx)
        elif self.handler is not None:
            return self.handler(entity, ctx)
        elif self.func is not None:
            return self.func(entity, ctx)
        return True

on_check_satisfied = HandlerRegistry(
    label="check_satisfied",
    aggregation_strategy="all_true")
"""
The global pipeline for evaluating local predicates. Handlers for predicates
should decorate methods with ``@on_check_satisfied.register(...)``.
"""

class Satisfiable(HasContext):

    predicates: list[Predicate] = Field(default_factory=list)

    @field_validator("predicates", mode="before")
    @classmethod
    def _convert_predicates(cls, data):
        if data is None:
            return []
        if isinstance(data, list):
            logger.debug(f"convert predicates: {data}")
            res = []
            for item in data:
                if isinstance(item, Predicate):
                    res.append(item)
                elif isinstance(item, dict):
                    res.append(Predicate(**item))
                elif isinstance(item, str):
                    res.append(Predicate(raw_expr=item))
                else:
                    raise ValueError(f"Invalid predicate: {item}")
            return res
        raise ValueError(f"Invalid predicate definition: {data}")

    @on_check_satisfied.register()
    def _check_my_predicates(self, *, ctx: StringMap) -> bool:
        for predicate in self.predicates:
            if not predicate.evaluate(self, ctx=ctx):
                return False
        return True

    def is_satisfied(self, *, ctx: StringMap = None) -> bool:
        ctx = ctx if ctx is not None else self.gather_context()
        return on_check_satisfied.execute_all_for(self, ctx=ctx)
