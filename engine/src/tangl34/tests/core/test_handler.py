from tangl34.core.handlers import Handler, HandlerRegistry, ServiceKind, HasHandlers
from tangl34.core.entity import Entity, StringMap

class DummyEntity(Entity):
    foo: int = None

def always_true(ctx): return True
def always_false(ctx): return False

def test_handler_priority_ordering():
    h1 = Handler(func=lambda x, y: 1, service=ServiceKind.CONTEXT, priority=1, label="h1")
    h2 = Handler(func=lambda x, y: 2, service=ServiceKind.CONTEXT, priority=10, label="h2")
    assert h1 < h2
    assert sorted([h2, h1]) == [h1, h2]

def test_handler_satisfied_with_predicate_and_criteria(monkeypatch):
    # caller matches only if foo=1
    caller = DummyEntity(foo=1)
    ctx = {"x": 42}
    # Handler with caller_criteria foo=1, predicate always_true
    h = Handler(
        func=lambda x, y: 1,
        service=ServiceKind.CONTEXT,
        priority=0,
        caller_criteria={"foo": 1},
        label="test",
        predicate=always_true,
    )
    assert h.is_satisfied(caller=caller, ctx=ctx)
    # Handler with caller_criteria foo=2, will NOT match
    h2 = Handler(
        func=lambda x, y: 1,
        service=ServiceKind.CONTEXT,
        priority=0,
        caller_criteria={"foo": 2},
        label="test",
        predicate=always_true,
    )
    assert not h2.is_satisfied(caller=caller, ctx=ctx)
    # Handler with predicate always_false
    h3 = Handler(
        func=lambda x, y: 1,
        service=ServiceKind.CONTEXT,
        priority=0,
        caller_criteria={"foo": 1},
        label="test",
        predicate=always_false,
    )
    assert not h3.is_satisfied(caller=caller, ctx=ctx)

def test_handlerregistry_register_and_iter_handlers():
    registry = HandlerRegistry()
    called = []

    @registry.register_handler(ServiceKind.CONTEXT, priority=5)
    def handler_a(ent, ctx):
        called.append("A")
        return "A"

    @registry.register_handler(ServiceKind.CONTEXT, priority=2)
    def handler_b(ent, ctx):
        called.append("B")
        return "B"

    handlers = list(registry.find_all(service=ServiceKind.CONTEXT))
    assert len(handlers) == 2
    # Should be sorted by priority ascending (2, 5)
    assert handlers[0].func.__name__ == "handler_b"
    assert handlers[1].func.__name__ == "handler_a"
    # Test the call
    e = DummyEntity()
    ctx = {}
    assert handlers[0].func(e, ctx) == "B"
    assert handlers[1].func(e, ctx) == "A"
    assert called == ["B", "A"]

def test_handlerregistry_find_all_handlers_for(monkeypatch):
    registry = HandlerRegistry()
    # Handler that matches foo=1
    @registry.register_handler(ServiceKind.CONTEXT, priority=1, caller_criteria={"foo": 1})
    def handler_c(ent, ctx): return "C"
    # Handler that matches foo=2
    @registry.register_handler(ServiceKind.CONTEXT, priority=2, caller_criteria={"foo": 2})
    def handler_d(ent, ctx): return "D"

    caller1 = DummyEntity(foo=1)
    caller2 = DummyEntity(foo=2)
    ctx = {}

    found1 = registry.find_all_for(caller1, ServiceKind.CONTEXT, ctx)
    found2 = registry.find_all_for(caller2, ServiceKind.CONTEXT, ctx)
    assert len(found1) == 1
    assert found1[0].func.__name__ == "handler_c"
    assert len(found2) == 1
    assert found2[0].func.__name__ == "handler_d"

def test_handlerregistry_register_returns_function():
    registry = HandlerRegistry()
    @registry.register_handler(ServiceKind.CONTEXT, priority=1, caller_criteria={"foo": 1})
    def handler_e(ent, ctx): return "E"
    # Should be callable as original function
    assert handler_e.__name__ == "handler_e"
    assert callable(handler_e)

def test_handler_mro_tie_break():
    class Base(Entity, HasHandlers): pass
    class Sub(Base): pass
    reg = HandlerRegistry()

    @reg.register_handler(ServiceKind.CONTEXT, priority=10, owner_cls=Base)
    def handler_base(ent, ctx): return "base"

    @reg.register_handler(ServiceKind.CONTEXT, priority=10, owner_cls=Sub)
    def handler_sub(ent, ctx): return "sub"

    base_inst = Base()
    sub_inst = Sub()
    ctx = {}

    # Should prefer Sub's handler for Sub instance, Base's handler for Base instance
    h_sub = reg.find_all_for(sub_inst, ServiceKind.CONTEXT, ctx)
    assert h_sub[0].func.__name__ == "handler_sub"
    h_base = reg.find_all_for(base_inst, ServiceKind.CONTEXT, ctx)
    assert h_base[0].func.__name__ == "handler_base"