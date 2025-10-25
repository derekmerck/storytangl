import types


class Obj(types.SimpleNamespace):
    pass

obj = Obj(prop1=9, prop2=10)

from tangl.core.runtime import Condition

badges = {
    'p1': Condition( expr="prop1 >= 10" ),
    'p2': Condition( expr="prop2 >= 10"),
    'both': Condition( expr="p1 and p2" ),
    'three': Condition(expr="both or p2")
}

import re
def nested_eval(condition: Condition, **kwargs):
    # kwargs = badges | kwargs
    print( condition )
    for k, v in kwargs.items():
        if re.findall(fr"\b{k}\b", condition.expr) and isinstance(v, Condition):
            kwargs[k] = v.nested_eval(**kwargs)
    return condition.eval(**kwargs)

Condition.nested_eval = nested_eval

# print( badges['p1'].nested_eval(ref=obj) )
# print( badges['p2'].nested_eval(ref=obj) )
# print( badges['both'].nested_eval(ref=obj) )
import functools

def add_badges(cls):

    s = f"class {cls.__name__}\n"
    for b, c in badges.items():

        def nested_eval(condition: Condition, ref):
            tokens = condition.expr.split()
            kwargs = {}
            for t in tokens:
                if hasattr(ref, t):
                    kwargs[t] = getattr(ref, t)
            return condition.eval(**kwargs)

        func = functools.partial(nested_eval, c)
        setattr( Obj, b, property( fget=func) )
        s += f"  {b}: bool\n"

    print( s )


add_badges(Obj)

print( obj.p1 )
print( obj.p2 )
print( obj.both )
print( obj.three )
