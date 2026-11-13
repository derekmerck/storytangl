"""Small deterministic controls for the opt-in lifecycle benchmark."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from benchmark_story_lifecycle import PRESETS, ROOT, story_data


@pytest.mark.parametrize("blocks", [PRESETS["small"], PRESETS["large"]])
def test_authored_shape_is_stable_and_cyclic(blocks: int) -> None:
    first = story_data(blocks, fanout=2)
    assert first == story_data(blocks, fanout=2)
    nodes = first["scenes"]["scene"]["blocks"]
    assert len(nodes) == blocks
    assert list(nodes)[0] == "block_0000"
    assert nodes[f"block_{blocks - 1:04d}"]["actions"][0]["successor"] == "block_0000"
    assert all(len(node["actions"]) == 2 for node in nodes.values())


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
