# Tests from v37.1 dispatch, modernized to match v37.2 api
import uuid

import pytest

from tangl.core.entity import Entity
from tangl.core.behavior import Behavior as Behavior, HandlerPriority, BehaviorRegistry as BehaviorRegistry, CallReceipt


class DummyEntity(Entity):
    foo: int = None

def always_true(ctx): return True
def always_false(ctx): return False


# ---------- Handlers & registry ----------

def test_handler_coerces_priority_from_str():

    for p in ["first", "FIRST", "0"]:
        h = Behavior(func=lambda c, ctx=None: True, priority=p)
        assert h.priority is HandlerPriority.FIRST


def test_handler_registry_register_and_iter_handlers():
    registry = BehaviorRegistry(label="test_handlers")
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

def test_handler_lt_tiebreaker_and_registry_sort():
    reg = BehaviorRegistry()
    calls = []

    def h1(c, ctx=None): calls.append(("h1", ctx)); return "r1"
    def h2(c, ctx=None): calls.append(("h2", ctx)); return "r2"

    reg.add_behavior(h1, priority=HandlerPriority.EARLY)
    reg.add_behavior(h2, priority=HandlerPriority.LATE)

    ctx = {"x": 1}
    c = Entity()
    receipts = list(reg.dispatch(c, ctx=ctx))
    assert [r.result for r in receipts] == ["r1", "r2"]
    assert [c[0] for c in calls] == ["h1", "h2"]

def test_run_handlers_utility_orders_input():
    # Manually construct handlers to check ordering
    def mk(func, prio):
        return Behavior(func=func, priority=prio)

    order = []
    hA = mk(lambda c, ctx=None: order.append("A"), HandlerPriority.NORMAL)
    hB = mk(lambda c, ctx=None: order.append("B"), HandlerPriority.LAST)
    hC = mk(lambda c, ctx=None: order.append("C"), HandlerPriority.EARLY)

    assert hC.priority is HandlerPriority.EARLY
    print( hC.sort_key() )

    # short sort and run, class method
    list(BehaviorRegistry().dispatch(Entity(), ctx={"ok": True}, extra_handlers=[hA, hB, hC]))
    assert order == ["C", "A", "B"]

def test_call_receipt_seq_monotonic():
    r1 = CallReceipt(behavior_id=uuid.uuid4(), result="x")
    r2 = CallReceipt(behavior_id=uuid.uuid4(), result="y")
    assert r2.seq == r1.seq + 1

def test_handler_ordering_and_receipts():
    from tangl.vm import ResolutionPhase as P
    regs = BehaviorRegistry()
    calls = []

    @regs.register(priority=HandlerPriority.FIRST)
    def a(c, ctx=None): calls.append(("a", ctx["phase"])); return "A"

    @regs.register(priority=HandlerPriority.NORMAL)
    def b(c, ctx=None): calls.append(("b", ctx["phase"])); return "B"

    ns = {"phase": P.VALIDATE, "results": []}
    c = Entity()
    receipts = list(regs.dispatch(c, ctx=ns))
    assert [r.result for r in receipts] == ["A", "B"]
    assert isinstance(receipts[0], CallReceipt)
    assert receipts[0].seq < receipts[1].seq  # monotonically increasing

def test_handler_run_one_picks_first():
    from tangl.vm import ResolutionPhase as P
    regs = BehaviorRegistry()

    @regs.register(priority=HandlerPriority.LATE)
    def late(c, ctx=None): return "late"

    @regs.register(priority=HandlerPriority.FIRST)
    def first(c, ctx=None): return "first"

    r = regs.dispatch(Entity(), ctx={"phase": P.VALIDATE, "results": []})
    assert next(r).result == "first"


def test_dispatch_registry_deterministic_order():
    registry = BehaviorRegistry()
    call_order: list[str] = []

    def register(name: str, priority: HandlerPriority | int) -> None:
        def func(c, ctx=None):
            call_order.append(name)
            return name

        registry.add_behavior(func, priority=priority, label=name)

    register("late", HandlerPriority.LATE)
    register("first", HandlerPriority.FIRST)
    register("early", HandlerPriority.EARLY)
    register("normal", HandlerPriority.NORMAL)

    call_order.clear()
    first_run = [receipt.result for receipt in registry.dispatch(Entity(), ctx={"run": 0})]
    expected = call_order.copy()

    assert first_run == expected

    for run in range(1, 4):
        call_order.clear()
        rerun = [receipt.result for receipt in registry.dispatch(Entity(), ctx={"run": run})]
        assert rerun == expected
        assert call_order == expected


def test_handler_priority_ordering():
    h1 = Behavior(func=lambda x, y: 1, priority=1, label="h1")
    h2 = Behavior(func=lambda x, y: 2, priority=10, label="h2")
    assert h1 < h2
    assert sorted([h2, h1]) == [h1, h2]

def test_handler_satisfied_with_predicate_and_criteria(monkeypatch):
    # caller matches only if foo=1
    caller = DummyEntity(foo=1)
    ctx = {"x": 42}
    # Behavior with caller_criteria foo=1, predicate always_true
    h = Behavior(
        func=lambda x, y: 1,
        priority=0,
        selection_criteria={"foo": 1, 'predicate': always_true},
        label="test",
    )
    assert h.satisfies(caller)
    # Behavior with caller_criteria foo=2, will NOT match
    h2 = Behavior(
        func=lambda x, y: 1,
        priority=0,
        selection_criteria={"foo": 2, 'predicate': always_true},
        label="test",
    )
    assert not h2.satisfies(caller)
    # Behavior with predicate always_false
    h3 = Behavior(
        func=lambda x, y: 1,
        priority=0,
        selection_criteria={"foo": 1, 'predicate': always_false},
        label="test"
    )
    assert not h3.satisfies(caller)


def test_handler_registry_register_returns_function():
    registry = BehaviorRegistry(label="test_handlers")
    @registry.register(priority=1, caller_criteria={"foo": 1})
    def handler_e(ent, ctx): return "E"
    # Should be callable as original function
    assert handler_e.__name__ == "handler_e"
    assert callable(handler_e)

def test_handlers_run_in_priority_order():
    reg = BehaviorRegistry()
    calls = []

    @reg.register(priority=HandlerPriority.LATE)
    def h3(c, ctx=None): calls.append("LATE"); return True

    @reg.register(priority=HandlerPriority.FIRST)
    def h1(c, ctx=None): calls.append("FIRST"); return True

    @reg.register(priority=HandlerPriority.EARLY)
    def h2(c, ctx=None): calls.append("EARLY"); return True

    list(reg.dispatch(Entity(), ctx=None))
    assert calls == ["FIRST", "EARLY", "LATE"]
