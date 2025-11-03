from __future__ import annotations

from tangl.core import Graph, Node
from tangl.vm import Frame, ResolutionPhase as P, Requirement, Dependency
from tangl.vm.provision import (
    GraphProvisioner,
    TemplateProvisioner,
    ProvisioningPolicy,
    PlanningReceipt,
    BuildReceipt,
)


def _frame_with_provisioners():
    graph = Graph(label="demo")
    cursor = graph.add_node(label="scene")
    frame = Frame(graph=graph, cursor_id=cursor.uid)

    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        TemplateProvisioner(layer="author"),
    ]

    @frame.local_behaviors.register(task="get_provisioners", priority=0)
    def _supply_provisioners(*_, **__):  # pragma: no cover - simple passthrough
        return provisioners

    return graph, cursor, frame


def _collect_build_receipts(frame: Frame) -> list[BuildReceipt]:
    receipts: list[BuildReceipt] = []
    for call in frame.phase_receipts.get(P.PLANNING, []):
        result = call.result
        if isinstance(result, list):
            receipts.extend(br for br in result if isinstance(br, BuildReceipt))
    return receipts


def test_planning_prefers_existing_offer():
    graph, cursor, frame = _frame_with_provisioners()
    existing = graph.add_node(label="door")
    requirement = Requirement(
        graph=graph,
        identifier="door",
        template={"obj_cls": Node, "label": "door"},
        policy=ProvisioningPolicy.ANY,
    )
    Dependency(graph=graph, source=cursor, requirement=requirement, label="needs_door")

    receipt = frame.run_phase(P.PLANNING)

    assert isinstance(receipt, PlanningReceipt)
    assert requirement.provider is existing
    assert receipt.attached == 1
    assert receipt.created == 0

    build_receipts = _collect_build_receipts(frame)
    assert any(br.provider_id == existing.uid for br in build_receipts)


def test_planning_marks_unresolved_requirement():
    graph, cursor, frame = _frame_with_provisioners()
    requirement = Requirement(
        graph=graph,
        identifier="missing",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=True,
    )
    Dependency(graph=graph, source=cursor, requirement=requirement, label="needs_missing")

    receipt = frame.run_phase(P.PLANNING)

    assert isinstance(receipt, PlanningReceipt)
    assert requirement.provider is None
    assert requirement.is_unresolvable is True
    assert receipt.unresolved_hard_requirements == [requirement.uid]
    assert _collect_build_receipts(frame)
