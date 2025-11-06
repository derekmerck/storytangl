import pytest

from tangl.core import Graph, Node
from tangl.vm.provision import (
    Provisioner,
    Requirement,
    ProvisioningPolicy,
    BuildReceipt,
    DependencyOffer,
    AffordanceOffer,
    GraphProvisioner,
    TemplateProvisioner,
    UpdatingProvisioner,
    CloningProvisioner,
    ProvisionCost,
)
from tangl.vm import Context, Frame, ResolutionPhase as P, Dependency, Affordance
from tangl.vm.dispatch.planning_v372 import plan_collect_offers, plan_select_and_apply
from tangl.core.behavior import CallReceipt

# pytest.skip(allow_module_level=True, reason="planning needs reimplemented")

# ---------- Provisioning orchestration ----------

def _frame_with_cursor():
    g = Graph(label="demo")
    n = g.add_node(label="anchor")
    return g, n

def test_provision_existing_success():
    g, n = _frame_with_cursor()
    target = g.add_node(label="T")
    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.EXISTING, identifier="T")
    assert req.satisfied_by(target)

    dep = Dependency(graph=g, source_id=n.uid, requirement=req, label="needs_T")
    frame = Frame(graph=g, cursor_id=n.uid)

    from tangl.vm.dispatch.planning_v372 import get_dependencies
    assert len( get_dependencies(n ) ) == 1
    assert len( get_dependencies(n, satisfied=False) ) == 1
    assert dep.satisfied_by(target)

    frame.run_phase(P.PLANNING)
    assert req.provider is target
    assert req.satisfied

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
    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CLONE,
        reference_id=ref.uid,
        template={"label": "RefClone"},
    )
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
        offer.operation for offer in offers if getattr(offer, "requirement", None) is req
    }

    assert ProvisioningPolicy.EXISTING in ops_for_requirement
    assert ProvisioningPolicy.CREATE in ops_for_requirement
    assert len(ops_for_requirement) >= 2

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

    prov = GraphProvisioner(node_registry=g)
    ctx = Context(graph=g, cursor_id=a.uid)
    offers = list(prov.get_dependency_offers(req, ctx=ctx))
    assert offers
    req.provider = offers[0].accept(ctx=ctx)
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

    prov = TemplateProvisioner()
    ctx = Context(graph=g, cursor_id=a.uid)
    offers = list(prov.get_dependency_offers(req, ctx=ctx))
    assert offers
    req.provider = offers[0].accept(ctx=ctx)
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

    failing_offer = DependencyOffer(
        requirement_id=req.uid,
        requirement=req,
        operation=ProvisioningPolicy.EXISTING,
        accept_func=lambda ctx: None,
        source_provisioner_id=provisioner.uid,
    )

    succeeding_offer = DependencyOffer(
        requirement_id=req.uid,
        requirement=req,
        operation=ProvisioningPolicy.EXISTING,
        accept_func=lambda ctx: winner,
        source_provisioner_id=provisioner.uid,
    )

    frame = Frame(graph=g, cursor_id=anchor.uid)
    ctx = frame.context
    ctx.call_receipts.clear()
    ctx.call_receipts.append(CallReceipt(
        behavior_id=provisioner.uid,
        result=[failing_offer, succeeding_offer]))

    builds = plan_select_and_apply(anchor, ctx=ctx)

    assert len(builds) == 1
    success = builds[0]
    assert success.accepted is True
    assert success.provider_id == winner.uid
    assert req.provider is winner
    assert req.is_unresolvable is False


def test_affordance_offers_are_prioritized_over_dependency_offers():
    g, anchor = _frame_with_cursor()
    existing = g.add_node(label="existing")

    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.ANY,
        identifier="existing",
        template={"obj_cls": Node, "label": "created"},
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=anchor.uid,
        requirement=req,
        label="needs_existing",
    )

    provisioner = Provisioner()

    def _accept_affordance(ctx: Context, destination: Node):
        req.provider = existing
        return Affordance(
            graph=ctx.graph,
            source=existing,
            destination=destination,
            requirement=req,
            label="use_existing",
        )

    affordance_offer = AffordanceOffer(
        label="use_existing",
        cost=ProvisionCost.DIRECT,
        accept_func=_accept_affordance,
        target_tags=set(),
    )

    affordance_offer.selection_criteria = {"source": "affordance"}

    created: list[Node] = []

    def _create() -> Node:
        node = Node(label="created")
        created.append(node)
        return node

    dependency_offer = DependencyOffer(
        requirement_id=req.uid,
        requirement=req,
        operation=ProvisioningPolicy.CREATE,
        accept_func=lambda ctx: _create(),
        source_provisioner_id=provisioner.uid,
    )
    dependency_offer.selection_criteria = {"source": "dependency"}

    frame = Frame(graph=g, cursor_id=anchor.uid)
    ctx = frame.context
    ctx.call_receipts.clear()
    ctx.call_receipts.append(
        CallReceipt(
            behavior_id=provisioner.uid,
            result=[affordance_offer, dependency_offer])
    )

    builds = plan_select_and_apply(anchor, ctx=ctx)

    assert req.provider is existing
    assert created == []
    assert builds
    assert builds[0].operation is ProvisioningPolicy.EXISTING

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
