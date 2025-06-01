from typing import Callable, Optional
from random import random
import logging

from pydantic import model_validator, BaseModel

from tangl.type_hints import StringMap, Expr
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.entity import Entity
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

g = {'__builtins__': safe_builtins, 'random': random}

class RuntimeObject(BaseModel):
    # predicates and runtime effects are normalized wrappers for a process definition
    structured_expr: Optional[StringMap] = None
    raw_expr: Optional[Expr] = None
    handler: Optional[BaseHandler] = None
    func: Optional[Callable[[Entity, StringMap], bool]] = None

    @model_validator(mode="after")
    def _check_only_one_mechanism(self):
        if sum([self.structured_expr is not None, self.raw_expr is not None, self.handler is not None, self.func is not None]) != 1:
            raise ValueError(f"Must specify exactly one mechanism for {self.__class__.__name__}.")
        return self

    @classmethod
    def eval_raw_expr(cls, expr: Expr, *, ctx: StringMap = None):
        return eval(expr, g, ctx)

    @classmethod
    def exec_raw_expr(cls, expr: Expr, *, ctx: StringMap) -> StringMap:
        logger.debug(f"exec_raw_expr: {expr} {ctx}")
        exec(expr, g, ctx)
        return ctx

    @classmethod
    def eval_structured_expr(cls, expr: StringMap, *, ctx: StringMap = None):
        raise NotImplementedError("Structured runtime exprs not yet implemented")

    @classmethod
    def exec_structured_expr(cls, expr: StringMap, *, ctx: StringMap = None):
        raise NotImplementedError("Structured runtime exprs not yet implemented")

    def model_dump(self, *args, **kwargs):
        if self.func:
            # This is an interoperability issue
            raise ValueError("Cannot serialize python callable runtime objects.")
        if self.handler:
            # todo: Should serialize handler predicates with a lookup source and reference,
            #       perhaps predicate handlers must be singleton members of an associated domain...
            raise NotImplementedError("Cannot serialize handler runtime objects by reference yet")
        return super().model_dump(*args, **kwargs)
