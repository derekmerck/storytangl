from __future__ import annotations
import pytest

from tangl.core import Graph, Node
from tangl.utils.hashing import hashing_func
from tangl.vm import (
    Frame,
    ChoiceEdge,
    Requirement,
    Dependency,
    Affordance,
    ProvisioningPolicy,
    PlanningReceipt,
    Patch,
)
from tangl.vm.resolution_phase import ResolutionPhase as P


def _collect_step_records(frame: Frame, step: int):
    marker = f"step-{step:04d}"
    return list(frame.records.get_section(marker, marker_type="frame"))


def _find_planning_receipt(records: list[object]) -> PlanningReceipt:
    for record in records:
        if isinstance(record, PlanningReceipt):
            return record
    raise AssertionError("planning receipt not found in records")


def test_planning_cycle_with_mixed_requirements():
    """Full planning pass reuses affordances, waives soft requirements, and creates new nodes."""

    g = Graph(label="integration_test")

    start = g.add_node(label="start")
    node_a = g.add_node(label="node_a")
    node_b = g.add_node(label="node_b")
    end = g.add_node(label="end")

    ChoiceEdge(graph=g, source_id=start.uid, destination_id=node_a.uid)
    ChoiceEdge(graph=g, source_id=node_a.uid, destination_id=node_b.uid)
    ChoiceEdge(graph=g, source_id=node_b.uid, destination_id=end.uid)

    req_x = Requirement[Node](
        graph=g,
        identifier="resource_x",
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "resource_x"},
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=node_a.uid,
        requirement=req_x,
        label="needs_resource_x",
    )

    req_y = Requirement[Node](
        graph=g,
        identifier="resource_y",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=False,
    )
    Dependency[Node](
        graph=g,
        source_id=node_a.uid,
        requirement=req_y,
        label="needs_resource_y",
    )

    service_z = g.add_node(label="service_z")
    req_z_aff = Requirement[Node](
        graph=g,
        identifier=service_z.uid,
        policy=ProvisioningPolicy.EXISTING,
        provider=service_z,
        hard_requirement=False,
    )
    Affordance[Node](
        graph=g,
        source_id=service_z.uid,
        destination_id=node_a.uid,
        requirement=req_z_aff,
        label="provides_service_z",
    )

    req_x_reuse = Requirement[Node](
        graph=g,
        identifier="resource_x",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=node_b.uid,
        requirement=req_x_reuse,
        label="reuses_resource_x",
    )

    req_w = Requirement[Node](
        graph=g,
        identifier="tool_w",
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "tool_w"},
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=node_b.uid,
        requirement=req_w,
        label="needs_tool_w",
    )

    frame = Frame(graph=g, cursor_id=start.uid)

    frame.run_phase(P.PLANNING)
    frame.run_phase(P.UPDATE)
    planning_receipt_start = frame.run_phase(P.FINALIZE)
    assert planning_receipt_start.created >= 1
    assert planning_receipt_start.attached >= 1
    assert len(planning_receipt_start.waived_soft_requirements) == 1
    assert not planning_receipt_start.unresolved_hard_requirements

    resource_x = g.find_one(label="resource_x")
    assert resource_x is not None
    assert req_x.provider == resource_x

    assert req_y.provider is None
    assert g.find_one(label="resource_y") is None

    assert req_z_aff.provider == service_z

    edge_to_a = next(start.edges_out(is_instance=ChoiceEdge))
    frame.follow_edge(edge_to_a)

    step_1_records = _collect_step_records(frame, 1)
    assert step_1_records
    planning_receipt_1 = _find_planning_receipt(step_1_records)

    assert planning_receipt_1.created >= 1
    assert planning_receipt_1.attached >= 1
    assert not planning_receipt_1.unresolved_hard_requirements

    edge_to_b = next(node_a.edges_out(is_instance=ChoiceEdge))
    frame.follow_edge(edge_to_b)

    step_2_records = _collect_step_records(frame, 2)
    assert step_2_records
    planning_receipt_2 = _find_planning_receipt(step_2_records)

    assert planning_receipt_2.attached == 0
    assert planning_receipt_2.created == 0
    assert not planning_receipt_2.builds
    assert not planning_receipt_2.unresolved_hard_requirements

    resource_x_nodes = [n for n in g.find_nodes(label="resource_x")]
    assert len(resource_x_nodes) == 1
    assert req_x_reuse.provider == resource_x_nodes[0]

    tool_w = g.find_one(label="tool_w")
    assert tool_w is not None
    assert req_w.provider == tool_w

    edge_to_end = next(node_b.edges_out(is_instance=ChoiceEdge))
    frame.follow_edge(edge_to_end)

    assert frame.cursor == end
    assert frame.step == 3

def test_softlock_detection_and_prevention():
    """Unresolvable hard requirements are surfaced in planning receipts and block progress."""

    g = Graph(label="softlock_test")

    start = g.add_node(label="start")
    gate = g.add_node(label="gate")
    end = g.add_node(label="end")

    ChoiceEdge(graph=g, source_id=start.uid, destination_id=gate.uid)
    edge_gate_to_end = ChoiceEdge(graph=g, source_id=gate.uid, destination_id=end.uid)

    req_key = Requirement[Node](
        graph=g,
        identifier="key",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=gate.uid,
        requirement=req_key,
        label="needs_key",
    )

    frame = Frame(graph=g, cursor_id=start.uid)

    frame.run_phase(P.PLANNING)
    frame.run_phase(P.UPDATE)
    planning_receipt = frame.run_phase(P.FINALIZE)

    assert planning_receipt.unresolved_hard_requirements == [req_key.uid]
    assert req_key.provider is None
    assert planning_receipt.softlock_detected is True

# @pytest.mark.xfail(reason="planning needs reimplemented")
def test_affordance_precedence_over_creation():
    """Affordances allow existing providers to satisfy dependencies instead of creating new nodes."""

    # Without an affordance, a hard dependency provisions a new companion.
    g_no_aff = Graph(label="affordance_baseline")
    start_no_aff = g_no_aff.add_node(label="start")
    scene_no_aff = g_no_aff.add_node(label="scene")
    ChoiceEdge(graph=g_no_aff, source_id=start_no_aff.uid, destination_id=scene_no_aff.uid)

    create_requirement = Requirement[Node](
        graph=g_no_aff,
        identifier="companion",
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "new_companion"},
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g_no_aff,
        source_id=scene_no_aff.uid,
        requirement=create_requirement,
        label="needs_companion",
    )

    frame_no_aff = Frame(graph=g_no_aff, cursor_id=start_no_aff.uid)
    frame_no_aff.follow_edge(next(start_no_aff.edges_out(is_instance=ChoiceEdge)))

    baseline_receipt = _find_planning_receipt(_collect_step_records(frame_no_aff, 1))
    assert baseline_receipt.created == 1
    assert create_requirement.provider is not None

    # With an affordance exposing an existing companion, no creation occurs.
    g = Graph(label="affordance_test")

    start = g.add_node(label="start")
    scene = g.add_node(label="scene")

    ChoiceEdge(graph=g, source_id=start.uid, destination_id=scene.uid)

    existing_companion = g.add_node(label="companion")

    companion_requirement = Requirement[Node](
        graph=g,
        identifier=existing_companion.uid,
        policy=ProvisioningPolicy.ANY,
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=scene.uid,
        requirement=companion_requirement,
        label="needs_companion",
    )

    Affordance[Node](
        graph=g,
        source_id=existing_companion.uid,
        destination_id=scene.uid,
        requirement=companion_requirement,
        label="has_companion",
    )

    frame = Frame(graph=g, cursor_id=start.uid)

    edge_to_scene = next(start.edges_out(is_instance=ChoiceEdge))
    frame.follow_edge(edge_to_scene)

    assert companion_requirement.provider == existing_companion

    planning_receipt = _find_planning_receipt(_collect_step_records(frame, 1))
    assert planning_receipt.created == 0


def test_hard_requirement_satisfied_by_affordance():
    """Hard requirements fulfilled through affordances stay resolved in receipts."""

    g = Graph(label="affordance_hard_requirement")

    start = g.add_node(label="start")
    scene = g.add_node(label="scene")
    ChoiceEdge(graph=g, source_id=start.uid, destination_id=scene.uid)

    guardian = g.add_node(label="guardian")

    hard_requirement = Requirement[Node](
        graph=g,
        identifier="guardian",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=scene.uid,
        requirement=hard_requirement,
        label="needs_guardian",
    )

    guardian_affordance_req = Requirement[Node](
        graph=g,
        identifier=guardian.uid,
        policy=ProvisioningPolicy.EXISTING,
        provider=guardian,
        hard_requirement=True,
    )
    Affordance[Node](
        graph=g,
        source_id=guardian.uid,
        destination_id=scene.uid,
        requirement=guardian_affordance_req,
        label="guardian_available",
    )

    frame = Frame(graph=g, cursor_id=start.uid)

    frame.run_phase(P.PLANNING)

    assert hard_requirement.provider is None

    frame.run_phase(P.UPDATE)
    planning_receipt = frame.run_phase(P.FINALIZE)

    assert hard_requirement.provider == guardian
    assert planning_receipt.unresolved_hard_requirements == []
    assert planning_receipt.attached >= 1

# @pytest.mark.xfail(reason="planning needs reimplemented")
def test_event_sourced_planning_replay():
    """Event-sourced planning produces deterministic patches that replay cleanly."""

    g = Graph(label="replay_test")

    start = g.add_node(label="start")
    node = g.add_node(label="node")

    ChoiceEdge(graph=g, source_id=start.uid, destination_id=node.uid)

    req = Requirement[Node](
        graph=g,
        identifier="created",
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "created"},
        hard_requirement=True,
    )
    Dependency[Node](
        graph=g,
        source_id=node.uid,
        requirement=req,
        label="needs_created",
    )

    baseline_hash = hashing_func(g._state_hash())
    baseline_graph = Graph.structure(g.unstructure())

    frame = Frame(graph=g, cursor_id=start.uid, event_sourced=True)

    edge_to_node = next(start.edges_out(is_instance=ChoiceEdge))
    frame.follow_edge(edge_to_node)

    step_records = _collect_step_records(frame, 1)
    assert step_records
    planning_receipt = _find_planning_receipt(step_records)

    patch = frame.phase_outcome.get(P.FINALIZE)
    assert isinstance(patch, Patch)
    assert patch.registry_state_hash == baseline_hash

    replayed_graph = patch.apply(baseline_graph)
    assert replayed_graph.find_one(label="created") is not None
    assert g.find_one(label="created") is None

    final_hash = hashing_func(g._state_hash())
    replayed_hash = hashing_func(replayed_graph._state_hash())
    assert final_hash != replayed_hash
    # maybe doesn't get cleared the same way anymore?
    # assert frame.event_watcher.events == []
