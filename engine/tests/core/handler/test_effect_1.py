from typing import ClassVar
import pytest
from tangl.core.entity import Entity
from tangl.core.handlers import HasEffects, on_apply_effects

class TestEffectNode(HasEffects, Entity):

    @on_apply_effects.register(priority=5)
    def custom_effect(self, ctx):
        ctx["y"] = "hello"

def test_apply_effects_increments():
    node = TestEffectNode(effects = ["x += 1", "x += 1"])
    ctx = {"x": 0, "y": ""}
    TestEffectNode.apply_effects(node, ctx=ctx)
    assert ctx["x"] == 2
    assert ctx["y"] == "hello"

def test_effect_order():

    class EffectOrderNode(HasEffects, Entity):
        @on_apply_effects.register(priority=1)
        def effect1(self, ctx):
            ctx["order"] = ctx.get("order", []) + ["first"]
        @on_apply_effects.register(priority=10)
        def effect2(self, ctx):
            ctx["order"] = ctx.get("order", []) + ["second"]
    node = EffectOrderNode()
    ctx = node.apply_effects()
    assert ctx["order"] == ["first", "second"]

@pytest.mark.skip(reason="doesn't work like this")
def test_effect_with_predicate():
    class EffectWithPred(HasEffects, Node):
        predicate: ClassVar = lambda ctx: ctx.get("apply", False)
        @HasEffects.on_apply_effects(priority=1, caller_criteria={"apply": True})
        def predicated(self, ctx):
            ctx["z"] = 99
    node = EffectWithPred()
    ctx = {"apply": True}
    EffectWithPred.apply_effects("before", node, node, ctx=ctx)
    assert ctx["z"] == 99
    ctx = {"apply": False}
    EffectWithPred.apply_effects("before", node, node, ctx=ctx)
    assert "z" not in ctx


# todo: integration tests:
#       - can update locals or attribs on another node
#       - render uses updated ctx when called sequentially

# todo: consider handler satisfied for caller
#       - caller criteria is stuff the caller has to _match_
#       - predicate is stuff the handler has to evaluate true against the context
