import uuid

from tangl.core.handler import Handler, HandlerPriority, HandlerRegistry, JobReceipt

# ---------- Handlers & registry ----------

def test_handler_lt_tiebreaker_and_registry_sort():
    reg = HandlerRegistry()
    calls = []

    def h1(ns): calls.append(("h1", ns)); return "r1"
    def h2(ns): calls.append(("h2", ns)); return "r2"

    reg.add(h1, priority=HandlerPriority.EARLY)
    reg.add(h2, priority=HandlerPriority.LATE)

    ns = {"x": 1}
    receipts = list(reg.run(ns))
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
    from tangl.vm.session import ResolutionPhase as P
    regs = HandlerRegistry()
    calls = []

    @regs.register(priority=HandlerPriority.FIRST)
    def a(ns): calls.append(("a", ns["phase"])); return "A"

    @regs.register(priority=HandlerPriority.NORMAL)
    def b(ns): calls.append(("b", ns["phase"])); return "B"

    ns = {"phase": P.VALIDATE, "results": []}
    receipts = list(regs.run(ns))
    assert [r.result for r in receipts] == ["A", "B"]
    assert isinstance(receipts[0], JobReceipt)
    assert receipts[0].seq < receipts[1].seq  # monotonically increasing

def test_handler_run_one_picks_first():
    from tangl.vm.session import ResolutionPhase as P
    regs = HandlerRegistry()

    @regs.register(priority=HandlerPriority.LATE)
    def late(ns): return "late"

    @regs.register(priority=HandlerPriority.FIRST)
    def first(ns): return "first"

    r = regs.run_one({"phase": P.VALIDATE, "results": []})
    assert r.result == "first"
