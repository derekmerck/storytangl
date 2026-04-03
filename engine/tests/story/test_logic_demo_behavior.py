"""Behavior tests for the phase-1 logic demo world."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.core import EntityTemplate, Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import Action, InitMode
from tangl.story.fragments import ContentFragment
from tangl.vm import Ledger
from tangl.vm.dispatch import do_journal
from tangl.vm.runtime.frame import PhaseCtx


def _logic_root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "logic_demo"


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _install_story_media_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )


def _compile_logic_world():
    bundle = WorldBundle.load(_logic_root())
    return WorldCompiler().compile(bundle)


def _make_ledger(*, world, story_label: str) -> Ledger:
    result = world.create_story(story_label, init_mode=InitMode.EAGER)
    return Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)


def _choice_by_text(ledger: Ledger, text: str) -> Action:
    return next(
        action
        for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if action.text == text
    )


def _journal_text(node) -> str:
    ctx = PhaseCtx(graph=node.graph, cursor_id=node.uid)
    fragments = do_journal(node, ctx=ctx)
    content = next(fragment for fragment in fragments if isinstance(fragment, ContentFragment))
    return content.content


def test_logic_demo_machine_blocks_keep_content_and_locals_empty() -> None:
    world = _compile_logic_world()
    logic_block_cls = world.class_registry["LogicBlock"]

    logic_templates = [
        template
        for template in Selector(has_payload_kind=logic_block_cls).filter(world.bundle.template_registry.values())
        if isinstance(template, EntityTemplate)
    ]

    assert logic_templates
    assert all(template.payload.content == "" for template in logic_templates)
    assert all(not template.payload.locals for template in logic_templates)


def test_logic_demo_journal_varies_by_machine_position(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_story_media_root(monkeypatch, tmp_path)
    world = _compile_logic_world()
    ledger = _make_ledger(world=world, story_label="logic_demo_journal")

    choose_machine_text = _journal_text(ledger.cursor)
    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the parity checker").uid)
    first_input_text = _journal_text(ledger.cursor)

    ledger.resolve_choice(_choice_by_text(ledger, "First bit = 1").uid)
    state_text = _journal_text(ledger.cursor)

    ledger.resolve_choice(_choice_by_text(ledger, "Second bit = 1").uid)
    output_text = _journal_text(ledger.cursor)

    assert choose_machine_text == "Choose a logic machine to inspect."
    assert first_input_text == "Parity checker: enter the first bit."
    assert state_text == "The XOR accumulator is odd so far. Enter the second bit."
    assert output_text == "Parity result: the two-bit input is even."


def test_logic_demo_journal_does_not_change_traversal_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_story_media_root(monkeypatch, tmp_path)
    world = _compile_logic_world()
    choices = [
        "Inspect the half adder",
        "A = 1",
        "B = 1",
    ]

    plain_ledger = _make_ledger(world=world, story_label="logic_demo_plain_run")
    journal_ledger = _make_ledger(world=world, story_label="logic_demo_journal_run")

    for text in choices:
        plain_ledger.resolve_choice(_choice_by_text(plain_ledger, text).uid)

        ctx = PhaseCtx(graph=journal_ledger.graph, cursor_id=journal_ledger.cursor_id)
        do_journal(journal_ledger.cursor, ctx=ctx)
        journal_ledger.resolve_choice(_choice_by_text(journal_ledger, text).uid)

    assert plain_ledger.cursor.label == "half_adder_output_01"
    assert journal_ledger.cursor.label == plain_ledger.cursor.label
