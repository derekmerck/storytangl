from tangl.core_next.task_handler import HandlerRegistry
from tangl.core_next.base import Entity
class E(Entity): pass
pipe = HandlerRegistry()
@pipe.register(caller_cls=E, priority=10)
def greet(entity, ctx): return "hi"
def test_pipeline_exec():
    out = pipe.execute_all(entity=E(), ctx={})
    assert out == ["hi"]