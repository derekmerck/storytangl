import pytest

from tangl.core import Graph, Node
from tangl.core.factory import Template
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
    ProvisioningContext,
    provision_node,
)
from tangl.vm import Context, Frame, ResolutionPhase as P, Dependency, Affordance
from tangl.vm.dispatch.planning import plan_collect_offers

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

    from tangl.vm.dispatch.planning import get_dependencies
    assert len( get_dependencies(n ) ) == 1
    assert len( get_dependencies(n, satisfied=False) ) == 1
    assert dep.satisfied_by(target)

    frame.run_phase(P.PLANNING)
    assert req.provider is None
    assert not req.satisfied

    frame.run_phase(P.UPDATE)
    frame.run_phase(P.FINALIZE)
    assert req.provider is target
    assert req.satisfied

def test_provision_existing_failure_sets_unresolvable():
    g, n = _frame_with_cursor()
    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.EXISTING, identifier="missing")
    Dependency[Node](graph=g, source_id=n.uid, requirement=req)
    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)
    assert req.provider is None
    assert not req.satisfied
    receipt = frame.run_phase(P.FINALIZE)
    assert receipt.unresolved_hard_requirements == [req.uid]
    assert receipt.softlock_detected is True

def test_provision_update_modifies_existing():
    g, n = _frame_with_cursor()
    target = g.add_node(label="T")
    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.UPDATE,
        identifier="T",
        template=Template[Node](label="T2"),
    )
    Dependency[Node](graph=g, source_id=n.uid, requirement=req)
    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)
    assert not req.satisfied
    assert target.label == "T"

    frame.run_phase(P.UPDATE)
    frame.run_phase(P.FINALIZE)
    assert req.satisfied and target.label == "T2"

def test_provision_clone_produces_new_uid():
    g, n = _frame_with_cursor()
    ref = g.add_node(label="Ref")
    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CLONE,
        reference_id=ref.uid,
        template=Template[Node](label="RefClone"),
    )
    Dependency[Node](graph=g, source_id=n.uid, requirement=req)
    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)
    assert not req.satisfied
    assert req.provider is None

    frame.run_phase(P.UPDATE)
    frame.run_phase(P.FINALIZE)
    assert req.satisfied and req.provider.label == "RefClone"
    assert req.provider.uid != ref.uid and req.provider in g


def test_plan_collect_offers_emits_multiple_operations_when_available():
    g, cursor = _frame_with_cursor()
    g.add_node(label="T")
    req = Requirement[Node](
        graph=g,
        identifier="T",
        template=Template[Node](label="T", obj_cls=Node),
        policy=ProvisioningPolicy.ANY,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=req, label="needs_T")

    ctx = Context(graph=g, cursor_id=cursor.uid)
    offers = plan_collect_offers(cursor, ctx=ctx)

    ops_for_requirement = {
        offer.operation for offer in offers if getattr(offer, "requirement", None) is req
    }

    assert ProvisioningPolicy.EXISTING in ops_for_requirement
    assert ProvisioningPolicy.CREATE_TEMPLATE in ops_for_requirement
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
                            template=Template[Node](label="B", obj_cls=Node, tags={"green"}),
                            policy=ProvisioningPolicy.CREATE_TEMPLATE)
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
    (ProvisioningPolicy.CREATE_TEMPLATE,   False, True),
    (ProvisioningPolicy.CREATE_TEMPLATE,   True,  True),   # won't resolve to the existing one by policy
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
                            template=Template[Node](label="T", obj_cls=Node))
    Dependency[Node](graph=g, source_id=anchor.uid, requirement=req, label="needs_T")

    frame = Frame(graph=g, cursor_id=anchor.uid)
    frame.run_phase(P.PLANNING)
    assert req.satisfied is False

    frame.run_phase(P.UPDATE)
    receipt = frame.run_phase(P.FINALIZE)

    assert req.satisfied is expected_satisfied
    if expected_satisfied:
        assert req.provider is not None
        if present and policy is ProvisioningPolicy.EXISTING:
            assert req.provider is existing, f"req.provider {req.provider} is not {existing}"
    else:
        assert req.provider is None
        assert req.uid in receipt.unresolved_hard_requirements or req.uid in receipt.waived_soft_requirements

def test_hard_requirement_unresolved_is_reported():
    g = Graph(label="demo")
    n = g.add_node(label="scene")

    hard_req = Requirement[Node](graph=g, hard=True, policy=ProvisioningPolicy.EXISTING,
                                 identifier="missing")
    Dependency[Node](graph=g, source_id=n.uid, requirement=hard_req, label="needs_missing")

    frame = Frame(graph=g, cursor_id=n.uid)
    frame.run_phase(P.PLANNING)

    assert hard_req.satisfied is False

    receipt = frame.run_phase(P.FINALIZE)

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
    frame.run_phase(P.PLANNING)

    # Requirement appears exactly once in the aggregated receipt after finalize.
    assert req.provider is None

    planning_receipt = frame.run_phase(P.FINALIZE)
    assert planning_receipt.unresolved_hard_requirements == [req.uid]
    assert planning_receipt.waived_soft_requirements == []


def test_provision_node_records_failure_when_offer_returns_none():
    g, anchor = _graph_and_anchor()

    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier="winner",
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=anchor.uid, requirement=req, label="needs_winner")

    winner = g.add_node(label="winner")

    class _TestProvisioner(Provisioner):
        def get_dependency_offers(self, requirement, *, ctx):
            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.EXISTING,
                accept_func=lambda ctx: None,
                source_provisioner_id=self.uid,
            )
            yield DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.EXISTING,
                accept_func=lambda ctx: winner,
                source_provisioner_id=self.uid,
            )

    provisioner = _TestProvisioner()
    prov_ctx = ProvisioningContext(graph=g, step=0)

    result = provision_node(anchor, [provisioner], ctx=prov_ctx)

    assert req.provider is None

    plan = result.primary_plan
    assert plan is not None

    vm_ctx = Context(graph=g, cursor_id=anchor.uid)
    receipts = plan.execute(ctx=vm_ctx)

    assert len(receipts) == 1
    failure = receipts[0]
    assert failure.accepted is False
    assert failure.provider_id is None


def test_provision_node_prioritizes_affordance_offers():
    g, anchor = _frame_with_cursor()
    existing = g.add_node(label="existing")

    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.ANY,
        identifier="existing",
        template=Template[Node](label="created", obj_cls=Node),
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=anchor.uid,
        requirement=req,
        label="needs_existing",
    )

    created: list[Node] = []

    class _TestProvisioner(Provisioner):
        def get_affordance_offers(self, node, *, ctx):
            offer = AffordanceOffer(
                label="use_existing",
                base_cost=ProvisionCost.DIRECT,
                cost=float(ProvisionCost.DIRECT),
                accept_func=lambda ctx, destination: _attach_existing(destination, ctx),
                target_tags=set(),
            )
            offer.source_provisioner_id = self.uid
            offer.selection_criteria = {"source": "affordance"}
            return [offer]

        def get_dependency_offers(self, requirement, *, ctx):
            offer = DependencyOffer(
                requirement_id=requirement.uid,
                requirement=requirement,
                operation=ProvisioningPolicy.CREATE_TEMPLATE,
                base_cost=ProvisionCost.CREATE,
                cost=float(ProvisionCost.CREATE),
                accept_func=lambda ctx: _create_created(),
                source_provisioner_id=self.uid,
            )
            offer.selection_criteria = {"source": "dependency"}
            return [offer]

    def _attach_existing(destination: Node, ctx: Context) -> Affordance:
        req.provider = existing
        return Affordance(
            graph=ctx.graph,
            source=existing,
            destination=destination,
            requirement=req,
            label="use_existing",
        )

    def _create_created() -> Node:
        node = Node(label="created")
        created.append(node)
        return node

    provisioner = _TestProvisioner()
    prov_ctx = ProvisioningContext(graph=g, step=0)

    result = provision_node(anchor, [provisioner], ctx=prov_ctx)

    plan = result.primary_plan
    assert plan is not None

    vm_ctx = Context(graph=g, cursor_id=anchor.uid)
    receipts = plan.execute(ctx=vm_ctx)

    assert req.provider is existing
    assert created == []
    assert receipts
    assert receipts[0].operation is ProvisioningPolicy.EXISTING

def test_affordance_creates_or_finds_source():
    g = Graph(label="demo")
    dst = g.add_node(label="terminal")

    req = Requirement[Node](graph=g, policy=ProvisioningPolicy.CREATE_TEMPLATE,
                            template=Template[Node](label="origin", obj_cls=Node))
    Affordance[Node](graph=g, destination_id=dst.uid, requirement=req, label="from_origin")

    frame = Frame(graph=g, cursor_id=dst.uid)
    frame.run_phase(P.PLANNING)

    assert not req.satisfied

    frame.run_phase(P.UPDATE)
    frame.run_phase(P.FINALIZE)

    assert req.satisfied
    assert g.find_nodes(label="origin"), "source should have been created"
