import pytest
from tangl34.core.handlers import Scope, ScopedSingleton, global_scope
from tangl34.core.handlers import ServiceKind
from tangl34.core.entity import Entity


# Dummy entity to pass as 'caller'
class Dummy(Entity): pass


# Have to reset global scope, at some point may need to 'reset' instead of clean?
@pytest.fixture(autouse=True)
def _clear_global_scope():
    global_scope.clear_handlers()
    yield
    global_scope.clear_handlers()


def test_class_handler_registration_and_discovery():
    class MyScope(Scope):
        @Scope.register_handler(ServiceKind.RENDER, priority=10)
        def render_me(self, ctx=None):
            return "from MyScope"

    s = MyScope()
    handlers = list(MyScope.gather_all_handlers_for(ServiceKind.RENDER, s, s))
    # Should discover the handler we just registered
    assert len(handlers) == 1
    assert handlers[0].func.__name__ == "render_me"
    assert handlers[0](s, {}) == "from MyScope"


def test_mro_handler_shadowing():
    class BaseScope(Scope):
        @Scope.register_handler(ServiceKind.RENDER, priority=10)
        def render_base(self, ctx=None): return "base"

    class SubScope(BaseScope):
        @Scope.register_handler(ServiceKind.RENDER, priority=10)
        def render_sub(self, ctx=None): return "sub"

    s = SubScope()
    handlers = list(SubScope.gather_all_handlers_for(ServiceKind.RENDER, s, s))
    # Should find both handlers, with subclass handler first
    assert [h.func.__name__ for h in handlers][:2] == ["render_sub", "render_base"]
    assert handlers[0](s, {}) == "sub"
    assert handlers[1](s, {}) == "base"


# todo: this won't work anymore, b/c handlers with the same priority don't get tie-broken by instance vs. cls registry in gather, gather gathers from all scopes and mros, then throws them all together and sorts them.
def test_instance_handler_overrides_class_handler():
    class MyScope(ScopedSingleton):

        @Scope.register_handler(ServiceKind.RENDER, priority=10)
        def render_me(self, ctx=None): return "class"

    s = MyScope(label="my_scope_instance")

    def render_instance(self, ctx=None): return "instance"

    s.register_instance_handler(ServiceKind.RENDER, render_instance, priority=10)

    handlers = list(MyScope.gather_all_handlers_for(ServiceKind.RENDER, s, s))
    # Should find instance handler first, then class handler
    names = [h.func.__name__ for h in handlers]
    assert names[0] == "render_instance"
    assert names[1] == "render_me"
    assert handlers[0](s, {}) == "instance"
    assert handlers[1](s, {}) == "class"


def test_handler_priority_ordering():
    class MyScope(Scope):
        @Scope.register_handler(ServiceKind.RENDER, priority=5)
        def render5(self, ctx=None): return "p5"

        @Scope.register_handler(ServiceKind.RENDER, priority=2)
        def render2(self, ctx=None): return "p2"

    s = MyScope()
    handlers = list(MyScope.gather_all_handlers_for(ServiceKind.RENDER, s, s))
    # Should be ordered by priority (lower first)
    assert [h.func.__name__ for h in handlers][:2] == ["render2", "render5"]


def test_global_scope_is_fallback():
    # Remove any previously registered handlers for cleanliness
    class EmptyScope(Scope): pass

    s = EmptyScope()

    # Register a global handler with unique output
    # todo: this pattern is weird, now we can't use the register_handlers decorator outside of the class definition
    @global_scope._scope_handlers.register(ServiceKind.RENDER, priority=50)
    def render_global(self, ctx=None): return "global"

    handlers = list(EmptyScope.gather_all_handlers_for(ServiceKind.RENDER, s, s))
    # Should find only the global handler
    assert any(h.func.__name__ == "render_global" for h in handlers)
    assert "global" in [h(s, {}) for h in handlers]


def test_registration_order_tiebreaker():
    class MyScope(Scope):
        @Scope.register_handler(ServiceKind.RENDER, priority=10)
        def a(self, ctx=None): return "a"

        @Scope.register_handler(ServiceKind.RENDER, priority=10)
        def b(self, ctx=None): return "b"

    s = MyScope()
    handlers = list(MyScope.gather_all_handlers_for(ServiceKind.RENDER, s, s))
    # With equal priority and scope, the first registered should come first
    assert handlers[0].func.__name__ == "a"
    assert handlers[1].func.__name__ == "b"

def test_handler_predicate_and_criteria(monkeypatch):
    class MyScope(Scope):

        @Scope.register_handler(ServiceKind.RENDER, priority=10, caller_criteria={"foo": 1})
        def h1(self, ctx=None): return "foo1"

        @Scope.register_handler(ServiceKind.RENDER, priority=10, caller_criteria={"bar": 2})
        def h2(self, ctx=None): return "bar2"

    s = MyScope(label="my_scope_instance")

    class Caller(Entity):
        foo: int = None
        bar: int = None

    c1 = Caller(foo=1)
    c2 = Caller(bar=2)
    # Should only get handlers that match caller_criteria
    handlers1 = list(MyScope.gather_all_handlers_for(ServiceKind.RENDER, c1, s))
    handlers2 = list(MyScope.gather_all_handlers_for(ServiceKind.RENDER, c2, s))
    assert handlers1[0].func.__name__ == "h1"
    assert handlers2[0].func.__name__ == "h2"


# todo: instance and class handlers are not tie-broken
def test_multiple_scopes_in_stack():
    # Stack two scopes: one with class handler, one with instance handler
    class ScopeA(Scope):
        @Scope.register_handler(ServiceKind.RENDER, priority=10)
        def ha(self, ctx=None): return "A"

    class ScopeB(ScopedSingleton):
        pass

    sa = ScopeA()
    sb = ScopeB(label="scope_b")

    def handler_b(self, ctx=None): return "B"

    sb.register_instance_handler(ServiceKind.RENDER, handler_b, priority=10)
    handlers = list(Scope.gather_all_handlers_for(ServiceKind.RENDER, sa, sb, sa))
    # Should find instance handler from ScopeB, then class handler from ScopeA
    assert handlers[0].func.__name__ == "handler_b"
    assert handlers[1].func.__name__ == "ha"