import uuid

import pytest

from tangl.core.entity import Entity
from tangl.core.dispatch import Handler, HandlerPriority, HandlerRegistry, JobReceipt

class DummyEntity(Entity):
    foo: int = None

def always_true(ctx): return True
def always_false(ctx): return False


# ---------- Handlers & registry ----------


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

def test_handler_lt_tiebreaker_and_registry_sort():
    reg = HandlerRegistry()
    calls = []

    def h1(ns): calls.append(("h1", ns)); return "r1"
    def h2(ns): calls.append(("h2", ns)); return "r2"

    reg.add(h1, priority=HandlerPriority.EARLY)
    reg.add(h2, priority=HandlerPriority.LATE)

    ns = {"x": 1}
    receipts = list(reg.run_all(ns))
    assert [r.result for r in receipts] == ["r1", "r2"]
    assert [c[0] for c in calls] == ["h1", "h2"]

def test_run_handlers_utility_orders_input():
    # Manually construct handlers to check ordering
    def mk(func, prio, reg_no):
        return Handler(func=func, priority=prio, reg_number=reg_no)

    order = []
    hA = mk(lambda ns: order.append("A"), HandlerPriority.NORMAL, 2)
    hB = mk(lambda ns: order.append("B"), HandlerPriority.LAST,   1)
    hC = mk(lambda ns: order.append("C"), HandlerPriority.EARLY,  0)

    list(HandlerRegistry.run_handlers({"ok": True}, [hA, hB, hC]))
    assert order == ["C", "A", "B"]

def test_job_receipt_seq_monotonic():
    r1 = JobReceipt(blame_id=uuid.uuid4(), result="x")
    r2 = JobReceipt(blame_id=uuid.uuid4(), result="y")
    assert r2.seq == r1.seq + 1

def test_handler_ordering_and_receipts():
    from tangl.vm.frame import ResolutionPhase as P
    regs = HandlerRegistry()
    calls = []

    @regs.register(priority=HandlerPriority.FIRST)
    def a(ns): calls.append(("a", ns["phase"])); return "A"

    @regs.register(priority=HandlerPriority.NORMAL)
    def b(ns): calls.append(("b", ns["phase"])); return "B"

    ns = {"phase": P.VALIDATE, "results": []}
    receipts = list(regs.run_all(ns))
    assert [r.result for r in receipts] == ["A", "B"]
    assert isinstance(receipts[0], JobReceipt)
    assert receipts[0].seq < receipts[1].seq  # monotonically increasing

def test_handler_run_one_picks_first():
    from tangl.vm.frame import ResolutionPhase as P
    regs = HandlerRegistry()

    @regs.register(priority=HandlerPriority.LATE)
    def late(ns): return "late"

    @regs.register(priority=HandlerPriority.FIRST)
    def first(ns): return "first"

    r = regs.run_one({"phase": P.VALIDATE, "results": []})
    assert r.result == "first"


def test_handler_priority_ordering():
    h1 = Handler(func=lambda x, y: 1, priority=1, label="h1")
    h2 = Handler(func=lambda x, y: 2, priority=10, label="h2")
    assert h1 < h2
    assert sorted([h2, h1]) == [h1, h2]

@pytest.mark.skip(reason="Not yet implemented")
def test_handler_satisfied_with_predicate_and_criteria(monkeypatch):
    # caller matches only if foo=1
    caller = DummyEntity(foo=1)
    ctx = {"x": 42}
    # Handler with caller_criteria foo=1, predicate always_true
    h = Handler(
        func=lambda x, y: 1,
        priority=0,
        caller_criteria={"foo": 1},
        label="test",
        predicate=always_true,
    )
    assert h.is_satisfied(caller=caller, ctx=ctx)
    # Handler with caller_criteria foo=2, will NOT match
    h2 = Handler(
        func=lambda x, y: 1,
        priority=0,
        caller_criteria={"foo": 2},
        label="test",
        predicate=always_true,
    )
    assert not h2.is_satisfied(caller=caller, ctx=ctx)
    # Handler with predicate always_false
    h3 = Handler(
        func=lambda x, y: 1,
        priority=0,
        caller_criteria={"foo": 1},
        label="test",
        predicate=always_false,
    )
    assert not h3.is_satisfied(caller=caller, ctx=ctx)


def test_handler_registry_register_returns_function():
    registry = HandlerRegistry(label="test_handlers")
    @registry.register(priority=1, caller_criteria={"foo": 1})
    def handler_e(ent, ctx): return "E"
    # Should be callable as original function
    assert handler_e.__name__ == "handler_e"
    assert callable(handler_e)

def test_handlers_run_in_priority_order():
    reg = HandlerRegistry()
    calls = []

    @reg.register(priority=HandlerPriority.LATE)
    def h3(ns): calls.append("LATE"); return True

    @reg.register(priority=HandlerPriority.FIRST)
    def h1(ns): calls.append("FIRST"); return True

    @reg.register(priority=HandlerPriority.EARLY)
    def h2(ns): calls.append("EARLY"); return True

    ns = {}
    list(reg.run_all(ns))
    assert calls == ["FIRST", "EARLY", "LATE"]
