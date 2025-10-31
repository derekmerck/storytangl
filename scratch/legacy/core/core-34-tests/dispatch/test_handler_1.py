import pytest

from tangl.core.entity import Entity
from tangl.core.behavior import Handler as BaseHandler, HandlerRegistry
from tangl.type_hints import StringMap

class DummyEntity(Entity):
    foo: int = None

def always_true(ctx): return True
def always_false(ctx): return False

def test_handler_registry_register_and_iter_handlers():
    registry = HandlerRegistry(label="test_handlers")
    called = []

    @registry.register(priority=5)
    def handler_a(ent, ctx):
        called.append("A")
        return "A"

    @registry.register(priority=2)
    def handler_b(ent, ctx):
        called.append("B")
        return "B"

    handlers = sorted(registry.find_all())
    assert len(handlers) == 2
    # Should be sorted by priority ascending (2, 5)
    assert handlers[0].func.__name__ == "handler_b"
    assert handlers[0].has_func_name("handler_b")
    assert handlers[0].matches(has_func_name="handler_b")

    assert handlers[1].func.__name__ == "handler_a"
    assert handlers[1].has_func_name("handler_a")
    assert handlers[1].matches(has_func_name="handler_a")

    # Test the call
    e = DummyEntity()
    ctx = {}
    assert handlers[0].func(e, ctx) == "B"
    assert handlers[1].func(e, ctx) == "A"
    assert called == ["B", "A"]

def test_handler_registry_find_all_handlers_for(monkeypatch):
    registry = HandlerRegistry(label="test_handlers")
    # BaseHandler that matches foo=1
    @registry.register(priority=1, caller_criteria={"foo": 1})
    def handler_c(caller: Entity, *, ctx): return "C"
    # BaseHandler that matches foo=2
    @registry.register(priority=2, caller_criteria={"foo": 2})
    def handler_d(caller: Entity, *, ctx): return "D"

    caller1 = DummyEntity(foo=1)
    caller2 = DummyEntity(foo=2)
    ctx = {}

    found1 = list(registry.find_all_for(caller1, ctx=ctx))
    found2 = list(registry.find_all_for(caller2, ctx=ctx))
    assert len(found1) == 1
    assert found1[0].func.__name__ == "handler_c"
    assert found1[0].has_func_name("handler_c")
    # assert found1[0].service_name == "test_handlers"

    assert len(found2) == 1
    assert found2[0].func.__name__ == "handler_d"

def test_handler_mro_tie_break():
    class Base(Entity): pass
    class Sub(Base): pass
    reg = HandlerRegistry(label="test_handlers")

    @reg.register(priority=10, owner_cls=Base)
    def handler_base(caller: Entity, *, ctx): return "base"

    @reg.register(priority=10, owner_cls=Sub)
    def handler_sub(caller: Entity, *, ctx): return "sub"

    base_inst = Base()
    sub_inst = Sub()
    ctx = {}

    # Should prefer Sub's handler for Sub instance, Base's handler for Base instance
    h_sub = list(reg.find_all_for(sub_inst, ctx=ctx))
    assert h_sub[0].func.__name__ == "handler_sub"
    h_base = list(reg.find_all_for(base_inst, ctx=ctx))
    assert h_base[0].func.__name__ == "handler_base"