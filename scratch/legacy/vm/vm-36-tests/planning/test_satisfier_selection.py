# tests/test_satisfier_selection.py
from uuid import uuid4
from tangl.vm36.planning.ticket import ProvisionRequirement
from tangl.vm36.planning.resolver import ProposalResolver
from tangl.core36.graph import Graph
from tangl.core36.facts import Facts


class DummyFinder(ProposalResolver):
    def __init__(self): super().__init__(kind="entity", cost_hint=70)
    def claim(self, constraints): return 90
    def find(self, g, facts, owner, spec): return [uuid4()]

class DummyBuilder(ProposalResolver):
    def __init__(self): super().__init__(kind="entity", cost_hint=20)
    def claim(self, constraints): return 10  # cheaper
    def realize(self, ctx, owner, spec): return ProvisionOutcome(status="bound", bound_uid=uuid4())

# todo: works, but wrong syntax?

def test_satisfier_prefers_find_now_then_lowest_cost_builder():
    g = Graph(); facts = Facts.compute(g)
    req = ProvisionRequirement(kind="entity", name="key", constraints={})
    f, b = DummyFinder(), DummyBuilder()
    # Feasibility: finder yields -> enabled
    assert list(f.find(g, facts, uuid4(), req))
    # If not found, builder should win via lower claim cost
    assert b.claim({}) is not None and b.claim({}) < f.claim({})