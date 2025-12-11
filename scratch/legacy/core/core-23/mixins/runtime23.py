# Reference for expressions-as-entities version

from __future__ import annotations
from typing import *
import random

import attr

from tangl.core import Entity
if TYPE_CHECKING:  # pragma: no cover
    Entity_ = Entity
else:
    Entity_ = object


@attr.define( init=False, slots=False )
class Condition(Entity):
    """Entity that can evaluate a condition"""

    #: Expression to evaluate, consumes string kwargs, ie, Condition("true") -> Condition(expr="true")
    expr: str = attr.ib(default=None, metadata={'consumes_str': True})

    def eval(self, **kwargs):
        ns = self.ns(**kwargs)
        code = compile(self.expr, "<string>", mode="eval")
        try:
            res = eval( code, ns )
        except (TypeError, NameError, AttributeError) as e:
            raise ValueError(f"Bad eval: {self.expr} raises '{e}'")

        # get rid of extraneous stuff (irrelevant op unless interrogating ns)
        ns.pop("__builtins__")
        ns.pop("random")

        return res

    check = eval

    def ns(self, **kwargs) -> dict:
        _ns = super().ns( **kwargs )
        _ns['random'] = random
        return _ns

    @classmethod
    def satisfied_by_ref(cls, conditions: bool | List, obj: Entity):
        if conditions is False:
            return False
        if conditions is True:
            return True
        for c in conditions:
            if not c.eval( r=obj ):
                return False
        return True

@attr.define( init=False, slots=False )
class Effect(Entity):
    """Entity that can apply an effect"""

    #: Expression to apply, consumes string kwargs, ie, Effect("a=2") -> Effect(expr="a=2")
    expr: str = attr.ib(default=None, metadata={'consumes_str': True})

    def exec(self, **kwargs):
        ns = self.ns(**kwargs)
        code = compile(self.expr, "<string>", mode="exec")
        try:
            exec( code, ns )
        except (TypeError, NameError, AttributeError) as e:
            raise ValueError(f"Bad exec: {self.expr} raises '{e}'")

        # get rid of extraneous stuff (irrelevant op unless interrogating ns)
        ns.pop("__builtins__")
        ns.pop("random")

        # write back locals
        for k, v in self.locals.items():
            if v != ns[k]:
                self.locals[k] = ns[k]

        # write back global primitives, anything with a dict should be
        # updated rather than recreated
        if hasattr(self.meta, "globals"):

            def isPrimitive(obj):
                return isinstance(obj, str) or \
                       not hasattr(obj, '__dict__')

            for k, v in self.meta.globals.items():
                if isPrimitive(v) and v != vars( ns['player'] )[k]:
                    self.meta.globals[k] = vars( ns['player'] )[k]

    apply = exec

    def ns(self, **kwargs) -> dict:
        _ns = super().ns( **kwargs )
        _ns['random'] = random
        return _ns


@attr.define( init=False, slots=False ) 
class RuntimeMixin(Entity_):

    #: List of conditions to test
    conditions: List[Condition] = attr.ib( factory=list )
    #: List of effects to apply
    effects: List[Effect] = attr.ib( factory=list )

    def avail(self, **kwargs) -> bool:
        """Check passes all conditions"""

        if not super().avail(**kwargs):
            # print( "Failed runtime super" )
            return False
        if self._dirty:
            return True
        return self.satisfied(**kwargs)

    def satisfied(self, **kwargs) -> bool:
        """All conditions satisfied"""
        for condition in self.conditions:
            if not condition.eval(**kwargs):
                return False
        return True

    def apply(self, **kwargs):
        """Apply all effects"""
        for effect in self.effects:
            effect.exec(**kwargs)
