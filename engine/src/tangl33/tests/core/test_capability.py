import pytest

from tangl33.core import ContextHandler, ResourceProvider, RedirectHandler
from tangl33.core import Tier, Requirement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
dummy_node = object()
dummy_driver = object()
dummy_graph = object()
ctx_empty = {}


def _ctx_layer(node, driver, graph, ctx):
    # returns an additional mapping layer
    return {"extra": 1}


def _redirect(node, driver, graph, ctx):
    # pretend we found an edge object
    return "EDGE42"


# ---------------------------------------------------------------------------
# Capability— behaviour & ordering
# ---------------------------------------------------------------------------
def test_contextcap_apply_and_predicate():
    cap = ContextHandler(_ctx_layer, tier=Tier.NODE, priority=0)
    assert cap.should_run(ctx_empty) is True
    result = cap.apply(dummy_node, dummy_driver, dummy_graph, ctx_empty)
    assert result == {"extra": 1}


def test_provisioncap_apply_and_provides():
    cap = ResourceProvider(provides={"shop"}, tier=Tier.GRAPH, owner_uid=None)
    out = cap.apply(dummy_node, dummy_driver, dummy_graph, ctx_empty)
    assert out is dummy_node
    assert "shop" in cap.provides


def test_capability_deterministic_sorting():
    a = ContextHandler(_ctx_layer, tier=Tier.NODE, priority=0)               # GATHER_CONTEXT / NODE / prio 0
    b = RedirectHandler(_redirect, tier=Tier.NODE, priority=0)               # CHECK_REDIRECTS / NODE / prio 0
    c = ContextHandler(_ctx_layer, tier=Tier.NODE, priority=10)              # higher priority → before 'a'

    # Expected order: phase, then tier, then -priority
    caps = [a, b, c]
    caps_sorted = sorted(caps)
    assert caps_sorted == [c, a, b]


# ---------------------------------------------------------------------------
# Requirement — equality, hashing, strategy
# ---------------------------------------------------------------------------
def test_requirement_equality_and_hashing():
    r1 = Requirement("shop", params={"at": "town"})
    r2 = Requirement("shop", params={"at": "town"})
    r3 = Requirement("shop", params={"at": "docks"})

    assert r1 == r2
    assert hash(r1) == hash(r2)
    assert r1 != r3


def test_requirement_strategy_invocation():
    calls = {}

    class DummyStrategy:
        def create(self, req, ctx):
            calls["called"] = req.key
            return "created-provider"

    strat = DummyStrategy()
    req = Requirement("dragon", strategy=strat)
    result = req.strategy.create(req, ctx_empty)
    assert result == "created-provider"
    assert calls["called"] == "dragon"


def test_direct_strategy_raises():
    req = Requirement("unknown")  # uses default DirectStrategy
    with pytest.raises(RuntimeError):
        req.strategy.create(req, ctx_empty)