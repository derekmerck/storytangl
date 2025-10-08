from __future__ import annotations
from tangl.core.dispatch import JobReceipt

from tangl.core import Graph, Node
from tangl.vm.planning.simple_planning_handlers import plan_collect_offers, plan_select_and_apply
from tangl.core.graph.edge import AnonymousEdge
from tangl.vm import (
    Frame,
    ResolutionPhase as P,
    Context,
    Requirement,
    Dependency,
    Affordance,
    ProvisioningPolicy,
)
from tangl.vm.planning import PlanningReceipt, BuildReceipt, ProvisionOffer, Provisioner
from tangl.utils.hashing import hashing_func


def _collect_build_receipts(frame: Frame) -> list:
    receipts = []
    for receipt in frame.phase_receipts.get(P.PLANNING, []):
        if isinstance(receipt.result, list):
            receipts.extend(
                item for item in receipt.result if isinstance(item, BuildReceipt)
            )
    return receipts


def test_plan_collect_offers_prioritizes_affordances_and_tags_sources():
    g = Graph(label="demo")
    cursor = g.add_node(label="scene")
    resource = g.add_node(label="cache")

    dep_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "generated"},
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=dep_req, label="needs_generated")

    aff_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier=resource.uid,
        hard_requirement=False,
    )
    Affordance[Node](
        graph=g,
        source_id=resource.uid,
        destination_id=cursor.uid,
        requirement=aff_req,
        label="has_cache",
    )

    frame = Frame(graph=g, cursor_id=cursor.uid)
    frame.run_phase(P.PLANNING)

    offer_receipts = frame.phase_receipts[P.PLANNING][0]
    offers = offer_receipts.result
    assert isinstance(offers, list)

    sources = [offer.selection_criteria.get("source") for offer in offers]
    assert "affordance" in sources
    assert "dependency" in sources

    first_dependency_index = sources.index("dependency")
    assert all(source == "affordance" for source in sources[:first_dependency_index])

    planning_receipt = frame.phase_outcome[P.PLANNING]
    assert isinstance(planning_receipt, PlanningReceipt)
    assert planning_receipt.attached == 1
    assert planning_receipt.created == 1


def test_planning_receipt_counts_created_unresolved_and_waived():
    g = Graph(label="demo")
    cursor = g.add_node(label="scene")

    created_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "created"},
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=created_req, label="needs_created")

    missing_hard = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier="missing_hard",
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=missing_hard, label="needs_missing_hard")

    missing_soft = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier="missing_soft",
        hard_requirement=False,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=missing_soft, label="needs_missing_soft")

    frame = Frame(graph=g, cursor_id=cursor.uid)
    frame.run_phase(P.PLANNING)

    planning_receipt = frame.phase_outcome[P.PLANNING]
    assert isinstance(planning_receipt, PlanningReceipt)
    assert planning_receipt.created == 1
    assert planning_receipt.unresolved_hard_requirements == [missing_hard.uid]
    assert planning_receipt.waived_soft_requirements == [missing_soft.uid]

    builds = _collect_build_receipts(frame)
    assert len(builds) == 3
    assert all(br.hard_req is not None for br in builds)


def test_event_sourced_frame_records_planning_receipt_and_patch():
    g = Graph(label="demo")
    start = g.add_node(label="start")
    scene = g.add_node(label="scene")

    created_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "projected"},
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=scene.uid, requirement=created_req, label="needs_projected")

    baseline_hash = hashing_func(g._state_hash())
    baseline_graph = Graph.structure(g.unstructure())

    frame = Frame(graph=g, cursor_id=start.uid, event_sourced=True)

    node_counts: list[int] = []

    @frame.local_domain.handlers.register(phase=P.JOURNAL, priority=0)
    def capture_node_count(cursor: Node, *, ctx, **_):
        node_counts.append(len(list(ctx.graph.find_nodes())))

    frame.follow_edge(AnonymousEdge(source=start, destination=scene))

    assert node_counts, "journal handler should have observed a graph snapshot"
    assert node_counts[0] >= 3  # start, scene, projected

    section = list(frame.records.get_section("step-0001", marker_type="frame"))
    assert section[0].record_type == "planning_receipt"
    assert section[-1].record_type == "patch"
    assert any(record.record_type == "fragment" for record in section)

    patch = frame.phase_outcome[P.FINALIZE]
    assert patch is not None and patch.record_type == "patch"
    assert patch.registry_state_hash == baseline_hash
    assert frame.event_watcher.events == []

    patched_graph = patch.apply(baseline_graph)
    assert patched_graph.find_one(label="projected") is not None


def test_plan_select_and_apply_handles_mixed_requirements():
    g = Graph(label="demo")
    cursor = g.add_node(label="cursor")
    existing = g.add_node(label="existing")

    hard_missing = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier="missing",
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=hard_missing, label="needs_missing")

    soft_create = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "created"},
        hard_requirement=False,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=soft_create, label="needs_created")

    satisfied = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.EXISTING,
        identifier=existing.uid,
        hard_requirement=True,
    )
    satisfied.provider = existing
    satisfied.is_unresolvable = True
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=satisfied, label="already_satisfied")

    ctx = Context(graph=g, cursor_id=cursor.uid)

    offers = plan_collect_offers(cursor, ctx=ctx)
    prov = Provisioner()
    offers.append(
        ProvisionOffer(
            requirement=satisfied,
            provisioner=prov,
            priority=0,
            operation=ProvisioningPolicy.EXISTING,
            accept_func=lambda: existing,
        )
    )
    ctx.job_receipts.clear()
    ctx.job_receipts.append(JobReceipt(result=offers))

    builds = plan_select_and_apply(cursor, ctx=ctx)
    build_by_req = {b.caller_id: b for b in builds}

    hard_receipt = build_by_req[hard_missing.uid]
    assert hard_receipt.accepted is False
    assert hard_receipt.reason == "no_offers"
    assert hard_missing.is_unresolvable is True

    soft_receipt = build_by_req[soft_create.uid]
    assert soft_receipt.accepted is True
    assert soft_create.provider is not None
    assert g.get(soft_create.provider_id) is soft_create.provider
    assert soft_create.is_unresolvable is False

    assert satisfied.is_unresolvable is False
    assert satisfied.provider is existing
