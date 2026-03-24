"""Static report and SVG tests for the logic demo graph analysis helpers."""

from __future__ import annotations

from pathlib import Path

from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import build_script_report, render_basic_svg, report_to_dict


def _logic_root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "logic_demo"


def _compile_logic_world():
    loader_bundle = WorldBundle.load(_logic_root())
    world = WorldCompiler().compile(loader_bundle)
    return world.bundle, world


def test_build_script_report_returns_expected_logic_demo_nodes_and_edges() -> None:
    _bundle, world = _compile_logic_world()

    report = build_script_report(world)
    nodes = {node.id: node for node in report.nodes}
    edges = {(edge.source_id, edge.target_id, edge.kind) for edge in report.edges}

    assert nodes["demo.choose_machine"].is_entry is True
    assert nodes["parity.parity_even_output"].is_terminal is True
    assert nodes["half_adder.half_adder_output_10"].scene_id == "half_adder"
    assert nodes["half_adder.half_adder_and_11"].gate_type == "AND"
    assert ("demo.choose_machine", "parity.parity_first_input", "action") in edges
    assert ("half_adder.half_adder_xor_11", "half_adder.half_adder_and_11", "continue") in edges


def test_build_script_report_is_deterministic_for_bundle_and_world() -> None:
    bundle, world = _compile_logic_world()

    first = report_to_dict(build_script_report(bundle))
    second = report_to_dict(build_script_report(world))

    assert first == second


def test_render_basic_svg_is_deterministic_and_marks_gate_shapes() -> None:
    _bundle, world = _compile_logic_world()
    report = build_script_report(world)

    first = render_basic_svg(report)
    second = render_basic_svg(report)

    assert first == second
    assert 'data-gate-type="INPUT"' in first
    assert 'data-gate-type="OUTPUT"' in first
    assert 'data-node-shape="diamond"' in first
    assert 'data-node-shape="hex"' in first
    assert "#4f83ff" in first
    assert "#ff8c42" in first
