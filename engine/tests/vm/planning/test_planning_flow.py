from __future__ import annotations
import pytest

from tangl.core import Graph, Node, BaseFragment
from tangl.core.graph.edge import AnonymousEdge
from tangl.vm import (
    Frame,
    ResolutionPhase as P,
    Requirement,
    Dependency,
    Affordance,
    ProvisioningPolicy,
    Patch
)
from tangl.vm.dispatch import planning
from tangl.vm.provision import PlanningReceipt, BuildReceipt
from tangl.utils.hashing import hashing_func

from conftest import _collect_build_receipts

# @pytest.mark.xfail(reason="planning needs reimplemented")
def test_plan_collect_offers_prioritizes_affordances_and_tags_sources():
    g = Graph(label="demo")
    cursor = g.add_node(label="scene")
    resource = g.add_node(label="cache")

    dep_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
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

    orchestrator_receipt = frame.phase_receipts[P.PLANNING][0]
    frontier_results = orchestrator_receipt.result
    assert isinstance(frontier_results, dict)

    offers = []
    for result in frontier_results.values():
        offers.extend(result.affordance_offers)
        for offer_list in result.dependency_offers.values():
            offers.extend(offer_list)

    sources = [offer.selection_criteria.get("source") for offer in offers]
    assert "affordance" in sources
    assert "dependency" in sources

    first_dependency_index = sources.index("dependency")
    assert all(source == "affordance" for source in sources[:first_dependency_index])

    frame.run_phase(P.UPDATE)
    planning_receipt = frame.run_phase(P.FINALIZE)
    assert isinstance(planning_receipt, PlanningReceipt)
    assert planning_receipt.attached == 1
    assert planning_receipt.created == 1

# @pytest.mark.xfail(reason="planning needs reimplemented")
def test_planning_receipt_counts_created_unresolved_and_waived():
    g = Graph(label="demo")
    cursor = g.add_node(label="scene")

    created_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
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

    frame.run_phase(P.UPDATE)
    planning_receipt = frame.run_phase(P.FINALIZE)
    assert isinstance(planning_receipt, PlanningReceipt)
    assert planning_receipt.created == 1
    assert planning_receipt.unresolved_hard_requirements == [missing_hard.uid]
    assert planning_receipt.waived_soft_requirements == [missing_soft.uid]

    builds = _collect_build_receipts(frame)
    assert len(builds) == 1
    assert builds[0].operation is ProvisioningPolicy.CREATE_TEMPLATE

# @pytest.mark.xfail(reason="planning needs reimplemented")
def test_event_sourced_frame_records_planning_receipt_and_patch():
    g = Graph(label="demo")
    start = g.add_node(label="start")
    scene = g.add_node(label="scene")

    created_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
        template={"obj_cls": Node, "label": "projected"},
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=scene.uid, requirement=created_req, label="needs_projected")

    baseline_hash = hashing_func(g._state_hash())
    baseline_graph = Graph.structure(g.unstructure())

    frame = Frame(graph=g, cursor_id=start.uid, event_sourced=True)

    node_counts: list[int] = []

    @frame.local_behaviors.register(task=P.JOURNAL, priority=0)
    def capture_node_count(cursor: Node, *, ctx, **_):
        node_counts.append(len(list(ctx.graph.find_nodes())))

    frame.follow_edge(AnonymousEdge(source=start, destination=scene))

    assert node_counts, "journal handler should have observed a graph snapshot"
    # assert node_counts[0] == 2  # start, scene before finalize applies plan

    projected = frame.graph.find_one(label="projected")
    assert projected is not None

    section = list(frame.records.get_section("step-0001", marker_type="frame"))
    assert isinstance( section[0], PlanningReceipt)
    assert isinstance( section[-1], Patch )
    assert any(isinstance(rec, BaseFragment) for rec in section)

    frame.run_phase(P.UPDATE)
    patch = frame.phase_outcome[P.FINALIZE]
    assert patch is not None and isinstance(patch, Patch)
    assert patch.registry_state_hash == baseline_hash
    # maybe doesn't get cleared on finalize anymore?
    # assert frame.event_watcher.events == []

    patched_graph = patch.apply(baseline_graph)
    assert patched_graph.find_one(label="projected") is not None


def test_planning_clears_frontier_cache_when_provisioners_missing(monkeypatch):
    g = Graph(label="demo")
    cursor = g.add_node(label="scene")

    created_req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
        template={"obj_cls": Node, "label": "created"},
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=cursor.uid, requirement=created_req, label="needs_created")

    frame = Frame(graph=g, cursor_id=cursor.uid)
    frame.run_phase(P.PLANNING)

    ctx = frame.context
    assert ctx.frontier_provision_results
    assert ctx.frontier_provision_plans

    monkeypatch.setattr(planning, "do_get_provisioners", lambda *_, **__: [])

    frame.run_phase(P.PLANNING)

    assert ctx.frontier_provision_results == {}
    assert ctx.frontier_provision_plans == {}
    assert ctx.planning_indexed_provisioners == []

    receipt = frame.run_phase(P.FINALIZE)
    assert isinstance(receipt, PlanningReceipt)
    assert receipt.builds == []
    assert receipt.frontier_node_ids == []
