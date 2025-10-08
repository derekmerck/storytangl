import uuid
from typing import Any, Optional, Literal

import pytest

from tangl.core.entity import Entity
from tangl.core import Graph, Node
from tangl.vm.planning import (
    Provisioner,
    Requirement,
    ProvisioningPolicy,
    ProvisionOffer,
    BuildReceipt,
)
from tangl.vm.planning.open_edge import Dependency, Affordance
from tangl.vm.frame import Frame, ResolutionPhase as P
from tangl.vm.context import Context
from tangl.vm.planning.simple_planning_handlers import plan_collect_offers, plan_select_and_apply
from tangl.core.dispatch import JobReceipt


# ---------- Provisioning orchestration ----------

def _frame_with_cursor():
    g = Graph(label="demo")
    n = g.add_node(label="anchor")
    return g, n

def test_provision_existing_success():
    g, n = _frame_with_cursor()
    target = g.add_node(label="T")
    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.EXISTING, identifier="T")
    Dependency[Node](graph=g, source_id=n.uid, requirement=req, label="needs_T")
    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)
    assert req.satisfied and req.provider is target

# @pytest.mark.xfail(reason="Needs orchestrator to link or mark unresolvable, previously in provisioner")
def test_provision_existing_failure_sets_unresolvable():
    g, n = _frame_with_cursor()
    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.EXISTING, identifier="missing")
    Dependency[Node](graph=g, source_id=n.uid, requirement=req)
    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)
    assert req.is_unresolvable and not req.satisfied

def test_provision_update_modifies_existing():
    g, n = _frame_with_cursor()
    target = g.add_node(label="T")
    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.UPDATE,
                            identifier="T", template={"label": "T2"})
    Dependency[Node](graph=g, source_id=n.uid, requirement=req)
    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)
    assert req.satisfied and target.label == "T2"

def test_provision_clone_produces_new_uid():
    g, n = _frame_with_cursor()
    ref = g.add_node(label="Ref")
    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.CLONE,
                            identifier="Ref", template={"label": "RefClone"})
    Dependency[Node](graph=g, source_id=n.uid, requirement=req)
    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)
    assert req.satisfied and req.provider.label == "RefClone"
    assert req.provider.uid != ref.uid and req.provider in g


def test_plan_collect_offers_emits_multiple_operations_when_available():
    g, cursor = _frame_with_cursor()
    g.add_node(label="T")
    req = Requirement[Node](
        graph=g,
        identifier="T",
        template={"obj_cls": Node, "label": "T"},
        policy=ProvisioningPolicy.ANY,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=req, label="needs_T")

    ctx = Context(graph=g, cursor_id=cursor.uid)
    offers = plan_collect_offers(cursor, ctx=ctx)

    ops_for_requirement = {
        offer.operation for offer in offers if offer.requirement.uid == req.uid
    }

    assert ProvisioningPolicy.EXISTING in ops_for_requirement
    assert ProvisioningPolicy.CREATE in ops_for_requirement
    assert len(ops_for_requirement) >= 2


@pytest.mark.xfail(reason="not working")
def test_provisioner_runs_offers_with_ns_and_returns_job_receipts():
    seen_ns = []
    # Build a provider that offers one ProvisionOffer and captures ns
    def get_affordances(ns):
        seen_ns.append(ns.copy())

        def accept(ns2):
            class Dummy(Entity): pass
            return Dummy(label="provided")
        return [ProvisionOffer(
            provider_id=uuid.uuid4(),
            predicate=None,
            _accept_func=accept,
            cost=1.0,
        )]

    prov = Provisioner(_get_affordances_func=get_affordances)

    ns = {"scope": "abc"}
    receipts = Provisioner.run([prov], ns=ns, requirement=None)
    assert len(receipts) == 1
    assert seen_ns == [ns]
    assert isinstance(receipts[0].result, Entity)

@pytest.mark.xfail(reason="not working")
def test_provisioner_blame_tuple_when_requirement_present():
    req = Requirement(dependency_id=uuid.uuid4(), criteria={"k": "v"})

    def get_offers(ns, requirement):
        def accept(_ns):
            class Dummy(Entity): pass
            return Dummy(label="dep")
        return [ProvisionOffer(
            provider_id=uuid.uuid4(),
            requirement_id=requirement.uid,
            predicate=None,
            _accept_func=accept,
            cost=1.0,
        )]

    prov = Provisioner(_get_affordances_func=None, _get_offers_func=get_offers)
    receipts = Provisioner.run([prov], ns={"x": 1}, requirement=req)
    assert len(receipts) == 1
    assert isinstance(receipts[0].blame_id, tuple) and len(receipts[0].blame_id) == 2

def test_edge_destination_none_branch_does_not_validate():
    g = Graph()
    n1 = g.add_node(label="S")
    e = g.add_edge(n1, None)
    # Should not raise on setting None
    e.destination = None
    assert e.destination_id is None
    # Then set a real destination
    n2 = g.add_node(label="D")
    e.destination = n2
    assert e.destination_id == n2.uid


# ---------- Planning ----------

def test_planning_resolves_dependency_existing():
    g = Graph()
    a = g.add_node(label="A")
    b = g.add_node(label="B", tags={"green"})

    req = Requirement[Node](graph=g,
                            identifier="B", criteria={"has_tags": {"green"}},
                            policy=ProvisioningPolicy.EXISTING)
    dep = Dependency(source_id=a.uid, requirement=req, graph=g)

    prov = Provisioner()
    req.provider = prov.resolve(req)
    assert req.provider is b
    assert req.satisfied
    assert dep.destination is b

def test_planning_create_when_missing():
    g = Graph()
    a = g.add_node(label="A")
    req = Requirement[Node](graph=g,
                            template={"obj_cls": "Node", "label": "B", "tags" :{"green"}},
                            policy=ProvisioningPolicy.CREATE)
    dep = Dependency(source_id=a.uid, requirement=req, graph=g)

    prov = Provisioner()
    req.provider = prov.resolve(req)
    assert req.provider is not None
    assert req.provider in g
    assert req.provider.get_label() == "B"
    assert dep.satisfied


def _graph_and_anchor():
    g = Graph(label="demo")
    anchor = g.add_node(label="anchor")
    return g, anchor

@pytest.mark.parametrize("policy, present, expected_satisfied", [
    (ProvisioningPolicy.EXISTING, True,  True),
    (ProvisioningPolicy.EXISTING, False, False),
    (ProvisioningPolicy.CREATE,   False, True),
    (ProvisioningPolicy.CREATE,   True,  True),   # won't resolve to the existing one by policy
])
def test_requirement_satisfaction_matrix(policy, present, expected_satisfied):
    g, anchor = _graph_and_anchor()
    if present:
        existing = g.add_node(label="T")
        identifier = "T"
    else:
        existing = None
        identifier = "T"
    req = Requirement[Node](graph=g, policy=policy, identifier=identifier,
                            template={"obj_cls": Node, "label": "T"})
    Dependency[Node](graph=g, source_id=anchor.uid, requirement=req, label="needs_T")

    frame = Frame(graph=g, cursor_id=anchor.uid)
    frame.run_phase(P.PLANNING)

    assert req.satisfied is expected_satisfied
    if expected_satisfied:
        assert req.provider is not None
        if present and policy is ProvisioningPolicy.EXISTING:
            assert req.provider is existing, f'req.provider {req.provider} is not {existing}'

@pytest.mark.xfail(reason="offers not working yet")
def test_selector_prefers_lowest_priority_and_stable_ordering():
    g = Graph(label="demo")
    n = g.add_node(label="scene")

    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.CREATE,
                            template={"obj_cls": Node, "label": "X"})

    Dependency[Node](graph=g, source_id=n.uid, requirement=req, label="needs_X")

    # Inject 3 offers in emission order; priorities: 5, 1, 1 (so choose the first of the priority-1 pair)

    from tangl.core import Handler
    from tangl.vm.planning import ProvisioningPolicy as PP

    class TestProvisioner(Provisioner, Handler):
        phase: Literal['PLANNING_PHASE'] = "PLANNING_PHASE"
        policy: PP = PP.CREATE
        requirement: Optional[Requirement[Node]] = None  # Irrelevant!
        template: dict[str, Any]
        priority: float

        def get_offers(self, requirement: Requirement) -> Optional[Offer | list[Offer]]:
            return Offer(
                requirement=requirement,
                provisioner=self,
                priority=self.priority
            )

        def accept_offer(self, offer: Offer) -> Entity:
            return Entity.structure(self.template)

    frame = Frame(graph=g, cursor_id=n.uid)

    params = [(5, 'bad'), (10, 'best'), (10, 'also_best')]
    for priority, suffix in params:
        frame.local_domain.handlers.add(
            TestProvisioner(
                priority=priority,
                template={"obj_cls": Node, "label": f"X_{suffix}"}
            )
        )

    offers = []
    def emit(priority, suffix):
        nonlocal offers

        prov = TemplateProvisioner(requirement=None, template={"obj_cls": Node, "label": f"X_{suffix}"})
        offer = Offer(requirement=req, provisioner=prov, priority=priority)
        offers.append(offer)
        return offer

    emit(5, "bad")
    first = emit(1, "best")
    emit(1, "also_good")

    frame.run_phase(P.PLANNING)

    assert req.satisfied
    assert req.provider.label == "X_best", "selector should pick lowest priority and earlier emission"


@pytest.mark.xfail(reason="multiple provisioners not working yet")
def test_equivalent_offers_are_deduplicated():
    g = Graph(label="demo")
    n = g.add_node(label="scene")
    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.CREATE,
                            template={"obj_cls": Node, "label": "K"})
    Dependency[Node](graph=g, source_id=n.uid, requirement=req)

    # Simulate two identical Provisioning offers (same template + target)
    Provisioning(graph=g, requirement=req, template={"obj_cls": Node, "label": "K"})
    Provisioning(graph=g, requirement=req, template={"obj_cls": Node, "label": "K"})

    frame = Frame(graph=g, cursor_id=n.uid)
    receipt = frame.run_phase(P.PLANNING)

    assert len(getattr(receipt, "accepted_offers", [])) == 1

def test_hard_requirement_unresolved_is_reported():
    g = Graph(label="demo")
    n = g.add_node(label="scene")

    hard_req = Requirement[Node](graph=g, hard=True, policy=ProvisioningPolicy.EXISTING,
                                 identifier="missing")
    Dependency[Node](graph=g, source_id=n.uid, requirement=hard_req, label="needs_missing")

    frame = Frame(graph=g, cursor_id=n.uid)
    receipt = frame.run_phase(P.PLANNING)

    assert hard_req.satisfied is False
    assert hasattr(receipt, "unresolved_hard_requirements")
    assert hard_req.uid in receipt.unresolved_hard_requirements


def test_hard_affordance_without_offers_marks_unresolvable_once():
    g = Graph(label="demo")
    destination = g.add_node(label="terminal")

    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier="missing",
        hard_requirement=True,
    )
    Affordance[Node](graph=g, destination_id=destination.uid, requirement=req, label="from_nowhere")

    frame = Frame(graph=g, cursor_id=destination.uid)
    planning_receipt = frame.run_phase(P.PLANNING)

    # Requirement is marked unresolved and appears exactly once in the aggregated receipt.
    assert req.is_unresolvable is True
    assert planning_receipt.unresolved_hard_requirements == [req.uid]

    build_receipts: list[BuildReceipt] = []
    for r in frame.phase_receipts[P.PLANNING]:
        if isinstance(r.result, list):
            build_receipts.extend([b for b in r.result if isinstance(b, BuildReceipt)])
        elif isinstance(r.result, BuildReceipt):
            build_receipts.append(r.result)

    assert len(build_receipts) == 1
    failure = build_receipts[0]
    assert failure.accepted is False
    assert failure.reason == "no_offers"
    assert failure.provider_id is None
    assert failure.caller_id == req.uid


def test_selector_skips_failed_offers_and_binds_first_success():
    g, anchor = _graph_and_anchor()

    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier="winner",
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=anchor.uid, requirement=req, label="needs_winner")

    winner = g.add_node(label="winner")

    provisioner = Provisioner()

    failing_offer = ProvisionOffer(
        label="fail",
        requirement=req,
        provisioner=provisioner,
        priority=1,
        operation=ProvisioningPolicy.EXISTING,
        accept_func=lambda: None,
    )

    succeeding_offer = ProvisionOffer(
        label="succeed",
        requirement=req,
        provisioner=provisioner,
        priority=2,
        operation=ProvisioningPolicy.EXISTING,
        accept_func=lambda: winner,
    )

    frame = Frame(graph=g, cursor_id=anchor.uid)
    ctx = frame.context
    ctx.job_receipts.clear()
    ctx.job_receipts.append(JobReceipt(result=[failing_offer, succeeding_offer]))

    builds = plan_select_and_apply(anchor, ctx=ctx)

    assert len(builds) == 1
    success = builds[0]
    assert success.accepted is True
    assert success.provider_id == winner.uid
    assert req.provider is winner
    assert req.is_unresolvable is False

@pytest.mark.xfail(reason="affordances not materialized and considered yet")
def test_affordance_creates_or_finds_source():
    g = Graph(label="demo")
    dst = g.add_node(label="terminal")

    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.CREATE,
                            template={"obj_cls": Node, "label": "origin"})
    Affordance[Node](graph=g, destination_id=dst.uid, requirement=req, label="from_origin")

    frame = Frame(graph=g, cursor_id=dst.uid)
    frame.run_phase(P.PLANNING)

    assert req.satisfied
    assert g.find_nodes(label="origin"), "source should have been created"