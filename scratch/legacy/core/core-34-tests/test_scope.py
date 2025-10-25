import pytest
from tangl.core.services import Scope, global_scope, ServiceKind, handler
from tangl.core.entity import Entity


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
        @handler(ServiceKind.RENDER, priority=10)
        def render_me(self, ctx=None):
            return "from MyScope"

    s = MyScope(label="MyScope")
    handlers = list(MyScope.gather_handlers(ServiceKind.RENDER, s, s))
    # Should discover the handler we just registered
    assert len(handlers) == 1
    assert handlers[0].func.__name__ == "render_me"
    assert handlers[0](s, {}) == "from MyScope"


def test_mro_handler_shadowing():
    class BaseScope(Scope):
        @handler(ServiceKind.RENDER, priority=10)
        def render_base(self, ctx=None): return "base"

    class SubScope(BaseScope):
        @handler(ServiceKind.RENDER, priority=10)
        def render_sub(self, ctx=None): return "sub"

    s = SubScope(label="SubScope")
    handlers = list(SubScope.gather_handlers(ServiceKind.RENDER, s, s))
    # Should find both handlers, with subclass handler first
    assert [h.func.__name__ for h in handlers][:2] == ["render_sub", "render_base"]
    assert handlers[0](s, {}) == "sub"
    assert handlers[1](s, {}) == "base"


def test_instance_handler_overrides_class_handler():
    class MyScope(Scope):

        @handler(ServiceKind.RENDER, priority=10)
        def render_me(self, ctx=None): return "class"

    s = MyScope(label="my_scope_instance")

    @s.register_instance_handler(ServiceKind.RENDER, priority=10)
    def render_instance(self, ctx=None): return "instance"


    handlers = list(MyScope.gather_handlers(ServiceKind.RENDER, s, s))
    # Should find instance handler first, then class handler
    names = [h.func.__name__ for h in handlers]
    assert names[0] == "render_instance"
    assert names[1] == "render_me"
    assert handlers[0](s, {}) == "instance"
    assert handlers[1](s, {}) == "class"


def test_handler_priority_ordering():
    class MyScope(Scope):
        @handler(ServiceKind.RENDER, priority=5)
        def render5(self, ctx=None): return "p5"

        @handler(ServiceKind.RENDER, priority=2)
        def render2(self, ctx=None): return "p2"

    s = MyScope(label="MyScope")
    handlers = list(MyScope.gather_handlers(ServiceKind.RENDER, s))
    # Should be ordered by priority (lower first)
    assert [h.func.__name__ for h in handlers][:2] == ["render2", "render5"]


def test_global_scope_is_fallback():
    # Remove any previously registered handlers for cleanliness
    class EmptyScope(Scope): pass

    s = EmptyScope(label="EmptyScope")

    # Register a global handler with unique output
    @global_scope.register_instance_handler(ServiceKind.RENDER, priority=50)
    def render_global(self, ctx=None): return "global"

    handlers = list(EmptyScope.gather_handlers(ServiceKind.RENDER, s))
    # Should find only the global handler
    assert any(h.func.__name__ == "render_global" for h in handlers)
    assert "global" in [h(s, {}) for h in handlers]


def test_registration_order_tiebreaker():
    class MyScope(Scope):
        @handler(ServiceKind.RENDER, priority=10)
        def a(self, ctx=None): return "a"

        @handler(ServiceKind.RENDER, priority=10)
        def b(self, ctx=None): return "b"

    s = MyScope(label="MyScope")
    handlers = list(MyScope.gather_handlers(ServiceKind.RENDER, s))
    # With equal priority and scope, the first registered should come first
    assert handlers[0].func.__name__ == "a"
    assert handlers[1].func.__name__ == "b"

def test_handler_predicate_and_criteria(monkeypatch):
    class MyScope(Scope):

        @handler(ServiceKind.RENDER, priority=10, caller_criteria={"foo": 1})
        def h1(self, ctx=None): return "foo1"

        @handler(ServiceKind.RENDER, priority=10, caller_criteria={"bar": 2})
        def h2(self, ctx=None): return "bar2"

    s = MyScope(label="my_scope_instance")

    class Caller(Entity):
        foo: int = None
        bar: int = None

    c1 = Caller(foo=1)
    c2 = Caller(bar=2)
    # Should only get handlers that match caller_criteria
    handlers1 = list(MyScope.gather_handlers(ServiceKind.RENDER, c1, s))
    handlers2 = list(MyScope.gather_handlers(ServiceKind.RENDER, c2, s))
    assert handlers1[0].func.__name__ == "h1"
    assert handlers2[0].func.__name__ == "h2"


# todo: instance and class handlers are not tie-broken
def test_multiple_scopes_in_stack():
    # Stack two scopes: one with class handler, one with instance handler
    class ScopeA(Scope):
        @handler(ServiceKind.RENDER, priority=10)
        def ha(self, ctx=None): return "A"

    class ScopeB(Scope):
        pass

    sa = ScopeA(label="scope_a")
    sb = ScopeB(label="scope_b")

    @sb.register_instance_handler(ServiceKind.RENDER, priority=10)
    def handler_b(self, ctx=None): return "B"

    handlers = list(Scope.gather_handlers(ServiceKind.RENDER, sa, sb))
    # Should find instance handler from ScopeB, then class handler from ScopeA
    assert handlers[0].func.__name__ == "handler_b"
    assert handlers[1].func.__name__ == "ha"