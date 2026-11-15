"""Small deterministic controls for the opt-in lifecycle benchmark.

Timing reference (2026-11-14)
----------------------------
These are observed ranges on one host, not portable expectations or CI limits.
At clean revision 5413a6cb617b9bc9519a8e34523052ab2f57dd08, Python 3.12.5,
macOS 26.5.2 arm64, the normal EAGER/JSON lifecycle with fanout 1 and checkpoint
cadence 10 produced the following inclusive Service choice times::

    Blocks  Profile   Median    Observed min-max
        20  baseline   19.6 ms    16.9-41.2 ms
        20  effects    21.3 ms    17.8-45.2 ms
       400  baseline  268.3 ms   227.9-362.9 ms
       400  effects   282.4 ms   264.6-343.1 ms

Each case used ten fresh-process samples, five in each profile order, with ten
choices per sample. Checkpoints and per-hop tracing remained enabled. The large
preset had 801 graph members; authored block count is not total graph size.

Host contention can produce an approximately 10x slowdown on large graphs.
An earlier same-revision run under suspected heavy host load reported large
choice medians of 2.37 s (baseline) and 2.71 s (effects), with calls up to 4.16 s.
The quieter reruns returned to the ranges above. This supports host contention
as the explanation; no individual competing application was isolated as the cause.

Before investigating an apparent regression, repeat the benchmark on a quiet
machine with the same revision, interpreter and parameters, in both profile
orders. Compare repeated medians and spread rather than one call. See the command
and timing boundaries in scripts/benchmark_story_lifecycle.py; correctness tests
deliberately contain no wall-clock assertions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from benchmark_story_lifecycle import EFFECT, PRESETS, ROOT, story_data, write_bundle


@pytest.mark.parametrize("blocks", [PRESETS["small"], PRESETS["large"]])
def test_authored_shape_is_stable_and_cyclic(blocks: int) -> None:
    first = story_data(blocks, fanout=2)
    assert first == story_data(blocks, fanout=2)
    nodes = first["scenes"]["scene"]["blocks"]
    assert len(nodes) == blocks
    assert list(nodes)[0] == "block_0000"
    assert nodes[f"block_{blocks - 1:04d}"]["actions"][0]["successor"] == "block_0000"
    assert all(len(node["actions"]) == 2 for node in nodes.values())
    effects = story_data(blocks, fanout=2, profile="effects")
    for node in effects["scenes"]["scene"]["blocks"].values():
        assert node.pop("effects") == [EFFECT]
    assert effects == first
    assert all("effects" not in node for node in nodes.values())


def test_tiny_worker_traverses_and_restores_json_store(tmp_path: Path) -> None:
    script = ROOT / "scripts/benchmark_story_lifecycle.py"
    result = subprocess.run(
        [sys.executable, str(script), "--worker", "--blocks", "4", "--choices", "10"],
        cwd=tmp_path, text=True, capture_output=True, check=True,
    )
    sample = json.loads(result.stdout)
    assert Path(sample["source_file"]).is_relative_to(ROOT / "engine/src")
    assert sample["counts"] == {
        "blocks": 4, "nodes": 5, "edges": 4, "actions": 4, "members": 9,
        "step_records": 10, "checkpoints": 3, "checkpoint_steps": [0, 1, 11],
        "choice_steps": 10, "cursor_steps": 11, "cursor_label": "block_0002",
    }
    assert sample["checkpoint_cadence_choices"] == 10
    assert len(sample["choice_s"]) == 10
    assert len(sample["dto_json_s"]) == len(sample["response_bytes"]) == 11
    assert all(size > 0 for size in sample["response_bytes"])


def test_cli_reports_json_summaries_from_checkout_despite_conflicting_path(tmp_path: Path) -> None:
    foreign = tmp_path / "foreign" / "tangl"
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text('raise AssertionError("wrong checkout")\n')
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/benchmark_story_lifecycle.py"),
         "--presets", "small", "--samples", "1", "--choices", "2"],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(foreign.parent)},
        text=True, capture_output=True, check=True,
    )
    report = json.loads(result.stdout)
    data = report["results"]["small"]
    assert report["profile"] == "baseline" and report["persistence"] == "json_file"
    assert data["blocks_requested"] == data["samples"][0]["counts"]["blocks"] == 20
    assert Path(data["samples"][0]["source_file"]).is_relative_to(ROOT / "engine/src")
    assert len(data["choice_by_position_s"]) == 2
    assert data["summary_s"]["create_story_s"]["median"] == data["samples"][0]["create_story_s"]


def test_cli_pairs_baseline_and_effects_with_matching_shape(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/benchmark_story_lifecycle.py"),
         "--presets", "small", "--profiles", "baseline", "effects", "--samples", "1", "--choices", "2"],
        cwd=tmp_path, text=True, capture_output=True, check=True,
    )
    report = json.loads(result.stdout)
    assert report["profile"] == "matched" and report["profiles"] == ["baseline", "effects"]
    profiles = report["results"]["small"]["profiles"]
    for name in ("baseline", "effects"):
        series = profiles[name]
        sample = series["samples"][0]
        assert series["profile"] == sample["profile"] == name
        assert series["blocks_requested"] == sample["counts"]["blocks"] == 20
        assert len(sample["choice_s"]) == len(series["choice_by_position_s"]) == 2
        assert isinstance(series["summary_s"]["create_story_s"]["median"], float)
    assert profiles["baseline"]["samples"][0]["counts"] == profiles["effects"]["samples"][0]["counts"]
    assert profiles["baseline"]["samples"][0]["selected_choices"] == (
        profiles["effects"]["samples"][0]["selected_choices"]
    )
    assert profiles["baseline"]["samples"][0]["benchmark_visits"] is None
    assert profiles["effects"]["samples"][0]["benchmark_visits"] == 3


def test_effects_service_json_rollback_and_continue(tmp_path: Path) -> None:
    from tangl.core import Selector
    from tangl.journal.fragments import ChoiceFragment
    from tangl.loaders import WorldBundle
    from tangl.loaders.compiler import WorldCompiler
    from tangl.persistence import PersistenceManagerFactory
    from tangl.service import ServiceManager
    from tangl.service.response import DirectEdgeRequest
    from tangl.service.world_registry import pop_manual_world, register_manual_world
    from tangl.story import InitMode, World
    from tangl.vm.replay import CheckpointRecord

    bundle = tmp_path / "lifecycle_baseline"
    write_bundle(bundle, 4, profile="effects")
    world = WorldCompiler().compile(WorldBundle.load(bundle))
    register_manual_world(world)
    try:
        store = tmp_path / "store"
        service = ServiceManager(PersistenceManagerFactory.json_file(base_path=store))
        user = service.create_user(secret="effects-test").details["user_id"]
        envelope = service.create_story(user_id=user, world_id=world.label, init_mode=InitMode.EAGER)
        with service.open_session(user_id=user) as session:
            ledger = session.ledger
            ids = (ledger.uid, ledger.graph.uid, ledger.cursor_id)
            assert ledger.graph.locals["benchmark_visits"] == 1
            assert (ledger.choice_steps, ledger.cursor_steps) == (0, 1)

        for index in range(3):
            choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment) and f.available)
            if index == 2:
                continuation = choice.edge_id
            envelope = service.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=choice.edge_id))
            with service.open_session(user_id=user) as session:
                assert session.ledger.graph.locals["benchmark_visits"] == index + 2
                if index == 2:
                    expected_hash = session.ledger.graph.value_hash()
                    expected_cursor_id = session.ledger.cursor_id
                if index == 1:
                    rollback_cursor_id = session.ledger.cursor_id

        reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=store))
        with reopened.open_session(user_id=user, write_back=True) as session:
            ledger = session.ledger
            assert (ledger.uid, ledger.graph.uid) == ids[:2]
            assert ledger.cursor_id == expected_cursor_id
            assert ledger.graph.locals["benchmark_visits"] == 4
            assert [c.step for c in Selector(has_kind=CheckpointRecord).filter(ledger.output_stream)] == [0, 1]
            ledger.rollback_to_step(3)
            assert ledger.graph.locals["benchmark_visits"] == 3
            assert (ledger.choice_steps, ledger.cursor_steps) == (2, 3)
            assert ledger.cursor.label == "block_0002" and ledger.cursor_id == rollback_cursor_id

        reopened.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=continuation))
        with reopened.open_session(user_id=user) as session:
            ledger = session.ledger
            assert (ledger.uid, ledger.graph.uid) == ids[:2]
            assert ledger.graph.locals["benchmark_visits"] == 4
            assert ledger.cursor.label == "block_0003"
            assert ledger.graph.value_hash() == expected_hash
    finally:
        pop_manual_world(world.label)
        World.clear_instances()
