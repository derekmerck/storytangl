"""Tests for Twine codec integration through world loading and materialization.

Organized by behavior:
- Clean fixture world: bundled Twine example compiles and materializes eagerly.
- Lossy temp worlds: structured losses propagate through WorldCompiler output.
"""
from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import InitMode, World
from tangl.story.episode import Action
from tangl.story.fragments import ChoiceFragment
from tangl.vm import Ledger
from tangl.vm.dispatch import do_journal
from tangl.vm.runtime.frame import PhaseCtx

import tangl.story  # noqa: F401 - ensure story handlers are registered


def _write_lossy_world(tmp_path: Path) -> WorldBundle:
    root = tmp_path / "twine_lossy"
    root.mkdir()
    (root / "world.yaml").write_text(
        """
label: twine_lossy
codec: twine
scripts: story.twee
        """.strip(),
        encoding="utf-8",
    )
    (root / "story.twee").write_text(
        """
:: StoryTitle
Lossy World

:: StoryData
{"start":"Begin","format":"Twine 2","format-version":"2.0"}

:: Begin
<<display "End">>
<<if $torch>>Lit<<endif>>
[[Go->End]]

:: End
Done.
        """.strip(),
        encoding="utf-8",
    )
    return WorldBundle.load(root)


def _as_fragment_list(fragments):
    if fragments is None:
        return []
    if isinstance(fragments, list):
        return fragments
    return [fragments]


def _write_stateful_world(tmp_path: Path) -> WorldBundle:
    root = tmp_path / "twine_stateful"
    root.mkdir()
    (root / "world.yaml").write_text(
        """
label: twine_stateful
codec: twine
scripts: story.twee
        """.strip(),
        encoding="utf-8",
    )
    (root / "story.twee").write_text(
        """
:: StoryTitle
Stateful World

:: StoryData
{"start":"Start","format":"Twine 2","format-version":"2.0"}

:: Start
[[Enter->Prep]]

:: Prep
<<set $gold to 1>>
<<if $gold is 1>>[[Spend->End][$gold += 1]]<<endif>>
<<if $gold is 2>>[[Locked->Miss]]<<endif>>

:: End
Done.

:: Miss
Miss.
        """.strip(),
        encoding="utf-8",
    )
    return WorldBundle.load(root)


def _write_start_seed_world(tmp_path: Path) -> WorldBundle:
    root = tmp_path / "twine_start_seed"
    root.mkdir()
    (root / "world.yaml").write_text(
        """
label: twine_start_seed
codec: twine
scripts: story.twee
        """.strip(),
        encoding="utf-8",
    )
    (root / "story.twee").write_text(
        """
:: StoryTitle
Start Seed World

:: StoryData
{"start":"Start","format":"Twine 2","format-version":"2.0"}

:: Start
<<set $torch to true>>
<<if $torch>>[[Go->End]]<<endif>>

:: End
Done.
        """.strip(),
        encoding="utf-8",
    )
    return WorldBundle.load(root)


class TestTwineReferenceWorld:
    """Tests for the clean bundled Twine reference world."""

    def test_bundle_loads(self) -> None:
        root = Path(__file__).resolve().parents[4] / "worlds" / "twine_reference"
        bundle = WorldBundle.load(root)

        assert bundle.manifest.label == "twine_reference"
        assert bundle.get_story_codec() == "twee3_1_0"
        assert bundle.get_script_paths() == [root / "story.twee"]

    def test_world_compiles_and_preserves_codec_state(self) -> None:
        root = Path(__file__).resolve().parents[4] / "worlds" / "twine_reference"
        bundle = WorldBundle.load(root)
        world = WorldCompiler().compile(bundle)

        assert isinstance(world, World)
        assert world.metadata["title"] == "The Ruined Tower"
        assert world.bundle.codec_id == "twee3_1_0"
        assert world.bundle.codec_state["story_format"] == "Twine 2"
        assert world.bundle.codec_state.get("loss_record_count", 0) == 0
        assert world.bundle.entry_template_ids == ["world.start"]
        assert "__source_files__" in world.bundle.source_map
        assert len(world.bundle.codec_state["passages"]) == 5

    def test_world_materializes_eagerly(self) -> None:
        root = Path(__file__).resolve().parents[4] / "worlds" / "twine_reference"
        bundle = WorldBundle.load(root)
        world = WorldCompiler().compile(bundle)
        result = world.create_story("twine_reference_story", init_mode=InitMode.EAGER)

        assert result.graph.label == "twine_reference_story"
        assert len(result.entry_ids) == 1
        assert result.graph.initial_cursor_id == result.entry_ids[0]
        assert result.report.materialized_counts.get("Scene") == 1
        assert result.report.materialized_counts.get("Block") == 5
        assert result.codec_id == "twee3_1_0"
        assert not result.report.unresolved_hard


class TestTwineLossPropagation:
    """Tests for end-to-end propagation of Twine decode losses."""

    def test_lossy_world_compiles_and_surfaces_structured_losses(self, tmp_path: Path) -> None:
        bundle = _write_lossy_world(tmp_path)
        world = WorldCompiler().compile(bundle)
        result = world.create_story("twine_lossy_story", init_mode=InitMode.EAGER)

        assert result.graph.initial_cursor_id is not None
        assert world.bundle.codec_state["loss_record_count"] >= 2
        assert any(
            record["kind"] == "unsupported_feature"
            for record in world.bundle.codec_state["loss_records"]
        )
        assert any("loss records" in warning for warning in world.metadata["codec_warnings"])


class TestTwineStatefulLowering:
    """Tests for runtime behavior of lowered Twine state and conditional links."""

    def test_start_passage_set_seeds_story_locals_for_first_frame(self, tmp_path: Path) -> None:
        bundle = _write_start_seed_world(tmp_path)
        world = WorldCompiler().compile(bundle)
        result = world.create_story("twine_start_seed_story", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.graph.locals["torch"] is True

        ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
        fragments = _as_fragment_list(do_journal(ledger.cursor, ctx=ctx))
        choices = {
            fragment.text: fragment.available
            for fragment in fragments
            if isinstance(fragment, ChoiceFragment)
        }

        assert ledger.cursor.label == "start"
        assert choices == {"Go": True}

    def test_stateful_links_apply_effects_and_gate_choices(self, tmp_path: Path) -> None:
        bundle = _write_stateful_world(tmp_path)
        world = WorldCompiler().compile(bundle)
        result = world.create_story("twine_stateful_story", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        start_action = next(
            ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        )
        ledger.resolve_choice(start_action.uid)

        assert ledger.cursor.label == "prep"
        assert ledger.graph.locals["gold"] == 1

        ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
        fragments = _as_fragment_list(do_journal(ledger.cursor, ctx=ctx))
        choices = {
            fragment.text: fragment.available
            for fragment in fragments
            if isinstance(fragment, ChoiceFragment)
        }

        assert choices == {"Spend": True, "Locked": False}

        spend_action = next(
            action
            for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
            if action.text == "Spend"
        )
        ledger.resolve_choice(spend_action.uid)

        assert ledger.cursor.label == "end"
        assert ledger.graph.locals["gold"] == 2
        assert world.bundle.codec_state.get("loss_record_count", 0) == 0
