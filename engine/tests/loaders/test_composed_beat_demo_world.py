"""Tests for the composed beat demo world bundle.

This world is the reference walkthrough for journal beat composition. The
assertions here pin one contribution channel each:

* data-scope chunk override — story ``locals`` vs block ``locals``
* handler-scope chunk override — APPLICATION vs AUTHOR ``gather_ns`` layers
* conditional render-time enrichment — namespace-gated ``on_journal``
* cross-phase enrichment — ``ctx.injected_journal_fragments`` from UPDATE
* post-merge composition — slot ordering, replacement, and the beat overlay
"""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.journal.fragments import ContentFragment, GroupFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _make_ledger() -> Ledger:
    bundle = WorldBundle.load(_repo_worlds_dir() / "composed_beat_demo")
    world = WorldCompiler().compile(bundle)
    result = world.create_story("composed_beat_demo", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    _prime_entry(ledger)
    return ledger


def _prime_entry(ledger: Ledger) -> None:
    """Seed entry JOURNAL output, mirroring the service's initial update."""
    frame = ledger.get_frame()
    frame.goto_node(ledger.cursor)
    ledger.cursor_steps += frame.cursor_steps
    ledger.cursor_id = frame.cursor.uid
    ledger.cursor_history.extend(frame.cursor_trace)
    ledger.call_stack_ids = [edge.uid for edge in frame.return_stack]


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


def _choose(ledger: Ledger, text_fragment: str) -> None:
    action = next(action for action in _actions(ledger) if text_fragment in action.text)
    ledger.resolve_choice(action.uid)


def _latest_step_fragments(ledger: Ledger) -> list:
    journal = ledger.get_journal()
    steps = [f.step for f in journal if f.step is not None and f.step >= 0]
    latest = max(steps)
    return [f for f in journal if f.step == latest]


def _content_texts(fragments: list) -> list[str]:
    return [str(f.content) for f in fragments if isinstance(f, ContentFragment)]


class TestComposedBeatDemoWorld:
    def test_world_registry_discovers_bundle(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "composed_beat_demo" in registry.bundles
        bundle = registry.bundles["composed_beat_demo"]
        assert bundle.manifest.metadata["title"] == "Composed Beat Demo"

    def test_domain_module_registers_beat_block(self) -> None:
        bundle = WorldBundle.load(_repo_worlds_dir() / "composed_beat_demo")
        world = WorldCompiler().compile(bundle)

        assert "BeatBlock" in world.class_registry

    def test_arrival_renders_chunk_overrides_and_beat_overlay(self) -> None:
        ledger = _make_ledger()
        assert ledger.cursor.label == "arrival"

        fragments = _latest_step_fragments(ledger)
        joined = " ".join(_content_texts(fragments))

        # data-scope: story-level ``dock_mood`` chunk interpolated into content
        assert "flat grey sky" in joined
        # handler-scope: AUTHOR gather_ns layer overrides the APPLICATION default
        assert "Old Maro looks up from his ledger" in joined
        assert "waves you through" not in joined
        # dialog markup composed earlier in the pipe survives beat assembly
        assert "Papers and cargo" in joined

        overlays = [f for f in fragments if isinstance(f, GroupFragment)]
        assert overlays
        assert overlays[-1].group_type == "beat"
        assert overlays[-1].member_ids

    def test_muddy_declare_assembles_full_beat(self) -> None:
        ledger = _make_ledger()
        _choose(ledger, "muddy")
        assert ledger.cursor.label == "gangway_muddy"
        # UPDATE-phase consequence landed on story-graph locals
        assert ledger.cursor.graph.locals["reputation"] == -1

        _choose(ledger, "manifest")
        assert ledger.cursor.label == "declare"

        fragments = _latest_step_fragments(ledger)
        texts = _content_texts(fragments)

        # block-scope ``locals`` override the story-scope chunk
        setting_idx = next(i for i, t in enumerate(texts) if "anything but quiet" in t)
        # cross-phase enrichment injected during UPDATE
        incident_idx = next(i for i, t in enumerate(texts) if "not listed at all" in t)
        # conditional enrichment fired because reputation slipped
        reaction_idx = next(i for i, t in enumerate(texts) if "mud you tracked" in t)
        # syuzhet slot order: setting before incident before reaction
        assert setting_idx < incident_idx < reaction_idx

        overlay = next(f for f in fragments if isinstance(f, GroupFragment))
        content_ids = {f.uid for f in fragments if isinstance(f, ContentFragment)}
        assert set(overlay.member_ids) == content_ids

    def test_clean_path_skips_conditional_enrichment(self) -> None:
        ledger = _make_ledger()
        _choose(ledger, "Wipe your boots")
        _choose(ledger, "manifest")

        texts = _content_texts(_latest_step_fragments(ledger))

        assert any("not listed at all" in t for t in texts)
        assert not any("mud you tracked" in t for t in texts)

    def test_fog_replaces_setting_fragment(self) -> None:
        ledger = _make_ledger()
        _choose(ledger, "Wipe your boots")
        _choose(ledger, "manifest")
        _choose(ledger, "warehouses")
        assert ledger.cursor.label == "fogbound"

        texts = _content_texts(_latest_step_fragments(ledger))

        assert any("rumor of shapes" in t for t in texts)
        assert not any("warehouse row stretches" in t for t in texts)
