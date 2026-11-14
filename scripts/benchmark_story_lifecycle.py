"""Measure ordinary synthetic-story Service lifecycles without timing gates.

Run from the checkout::

    .venv/bin/python scripts/benchmark_story_lifecycle.py --presets small large --samples 5 --choices 10

Each sample runs in a fresh interpreter with its own bundle, JSON store and caches.
Imports and bundle generation precede timing. Bundle load reads the manifest; script
decode occurs with compilation. Compilation and manual world registration are combined;
create and choice timings are inclusive Service calls (including persistence), while
DTO/JSON serialization is timed separately. Choices reuse a warm world but reopen the
persisted session normally. These observations do not measure browser or network time.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
PRESETS = {"small": 20, "large": 400}


def story_data(blocks: int, fanout: int = 1) -> dict:
    """Create stable near-native author data with a forward cyclic topology."""
    if blocks < 2 or not 1 <= fanout < blocks:
        raise ValueError("blocks must be >= 2 and fanout must be between 1 and blocks - 1")
    return {
        "label": "lifecycle_baseline",
        "metadata": {"title": "Lifecycle baseline", "start_at": "scene.block_0000"},
        "scenes": {"scene": {"blocks": {
            f"block_{index:04d}": {
                "content": f"Static passage {index:04d}.",
                "actions": [
                    {"text": f"Continue {offset}",
                     "successor": f"block_{(index + offset) % blocks:04d}"}
                    for offset in range(1, fanout + 1)
                ],
            }
            for index in range(blocks)
        }}},
    }


def write_bundle(path: Path, blocks: int, fanout: int = 1) -> None:
    import yaml

    path.mkdir(parents=True, exist_ok=True)
    (path / "world.yaml").write_text(yaml.safe_dump({
        "label": "lifecycle_baseline", "scripts": "script.yaml",
        "metadata": {"title": "Lifecycle baseline", "start_at": "scene.block_0000"},
    }, sort_keys=False), encoding="utf-8")
    (path / "script.yaml").write_text(yaml.safe_dump(story_data(blocks, fanout), sort_keys=False),
                                       encoding="utf-8")


def measure_sample(blocks: int, fanout: int, choices: int, root: Path) -> dict:
    """Exercise the public lifecycle once; caller isolates the process and paths."""
    from tangl.core import Edge, Node, Selector
    from tangl.journal.fragments import ChoiceFragment, ContentFragment
    from tangl.loaders import WorldBundle
    from tangl.loaders.compiler import WorldCompiler
    from tangl.persistence import PersistenceManagerFactory
    from tangl.service import ServiceManager
    from tangl.service.response import DirectEdgeRequest
    from tangl.service.world_registry import pop_manual_world, register_manual_world
    from tangl.story import Action, Block, InitMode
    from tangl.vm.replay import CheckpointRecord, StepRecord
    import tangl

    bundle_path = root / "lifecycle_baseline"
    write_bundle(bundle_path, blocks, fanout)
    start = perf_counter()
    bundle = WorldBundle.load(bundle_path)
    loaded = perf_counter()
    world = WorldCompiler().compile(bundle)
    register_manual_world(world)
    compiled = perf_counter()
    try:
        store = root / "store"
        manager = ServiceManager(PersistenceManagerFactory.json_file(base_path=store))
        user_id = manager.create_user(secret="benchmark-reader").details["user_id"]
        start_create = perf_counter()
        envelope = manager.create_story(user_id=user_id, world_id=world.label, init_mode=InitMode.EAGER)
        created = perf_counter()

        def encode(value):
            begin = perf_counter()
            data = json.dumps(value.to_dto(), separators=(",", ":")).encode("utf-8")
            return perf_counter() - begin, len(data)

        serialization = [encode(envelope)]
        choice_times = []
        for index in range(choices):
            offered = [item for item in envelope.fragments
                       if isinstance(item, ChoiceFragment) and item.available]
            if not offered or not any(isinstance(item, ContentFragment) for item in envelope.fragments):
                raise RuntimeError(f"Missing content or available choice at iteration {index}")
            choice = offered[0]
            begin = perf_counter()
            envelope = manager.resolve_choice(
                user_id=user_id,
                request=DirectEdgeRequest(edge_id=choice.edge_id, payload=choice.activation_payload),
            )
            choice_times.append(perf_counter() - begin)
            serialization.append(encode(envelope))

        with manager.open_session(user_id=user_id) as session:
            ledger = session.ledger
            graph = ledger.graph
            checkpoints = list(Selector(has_kind=CheckpointRecord).filter(ledger.output_stream))
            counts = {
                "blocks": len(list(graph.find_all(Selector(has_kind=Block)))),
                "nodes": len(list(graph.find_all(Selector(has_kind=Node)))),
                "edges": len(list(graph.find_all(Selector(has_kind=Edge)))),
                "actions": len(list(graph.find_all(Selector(has_kind=Action)))),
                "members": len(graph.members),
                "step_records": len(list(Selector(has_kind=StepRecord).filter(ledger.output_stream))),
                "checkpoints": len(checkpoints),
                "checkpoint_steps": [item.step for item in checkpoints],
                "choice_steps": ledger.choice_steps,
                "cursor_steps": ledger.cursor_steps,
                "cursor_label": ledger.cursor.label,
            }
            identity_and_state = (ledger.uid, graph.uid, ledger.cursor_id,
                                  ledger.choice_steps, ledger.cursor_steps, list(ledger.cursor_history))
            cadence = ledger.checkpoint_cadence
        reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=store))
        with reopened.open_session(user_id=user_id) as session:
            saved = session.ledger
            if (saved.uid, saved.graph.uid, saved.cursor_id, saved.choice_steps,
                    saved.cursor_steps, saved.cursor_history) != identity_and_state:
                raise AssertionError("JSON reopen changed ledger identity or traversal state")
        return {
            "source_file": str(Path(tangl.__file__).resolve()),
            "bundle_load_s": loaded - start,
            "compile_and_register_s": compiled - loaded,
            "create_story_s": created - start_create,
            "choice_s": choice_times,
            "dto_json_s": [duration for duration, _ in serialization],
            "response_bytes": [size for _, size in serialization],
            "counts": counts,
            "checkpoint_cadence_choices": cadence,
        }
    finally:
        pop_manual_world(world.label)


def summary(values: list[float]) -> dict[str, float]:
    return {"median": statistics.median(values), "min": min(values), "max": max(values)}


def run(presets: list[str], samples: int, choices: int, fanout: int) -> dict:
    if samples < 1 or choices < 1:
        raise ValueError("samples and choices must be positive")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                              capture_output=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                                capture_output=True, check=True).stdout.strip())
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(ROOT / "engine/src"), env.get("PYTHONPATH"))))
    results = {}
    for preset in presets:
        rows = []
        for _ in range(samples):
            worker = subprocess.run([
                sys.executable, str(Path(__file__).resolve()), "--worker", "--blocks",
                str(PRESETS[preset]), "--fanout", str(fanout), "--choices", str(choices),
            ], cwd=ROOT, env=env, text=True, capture_output=True)
            if worker.stderr:
                sys.stderr.write(worker.stderr)
            worker.check_returncode()
            rows.append(json.loads(worker.stdout))
        results[preset] = {
            "blocks_requested": PRESETS[preset], "samples": rows,
            "summary_s": {name: summary([row[name] for row in rows]) for name in
                          ("bundle_load_s", "compile_and_register_s", "create_story_s")},
            "choice_summary_s": summary([value for row in rows for value in row["choice_s"]]),
            "choice_by_position_s": [summary([row["choice_s"][index] for row in rows])
                                     for index in range(choices)],
            "dto_json_summary_s": summary([value for row in rows for value in row["dto_json_s"]]),
        }
    return {"revision": revision, "dirty": dirty, "python": sys.version, "platform": platform.platform(),
            "profile": "baseline", "init_mode": "EAGER", "persistence": "json_file",
            "conditions": (
                "fresh worker and store per sample; imports, bundle writing and user creation excluded; "
                "direct manifest load; script decode, compile and manual registration combined; "
                "choices reload persisted sessions; no network or browser"
            ),
            "samples_per_preset": samples, "choices_per_sample": choices, "fanout": fanout,
            "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--presets", nargs="+", choices=tuple(PRESETS), default=list(PRESETS))
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--choices", type=int, default=10)
    parser.add_argument("--fanout", type=int, default=1)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--blocks", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        with tempfile.TemporaryDirectory(prefix="storytangl-benchmark-") as directory:
            root = Path(directory)
            os.environ["TANGL_SERVICE__PATHS__CACHE_DATA"] = f"@path {root / 'cache'}"
            os.environ["TANGL_SERVICE__PATHS__STORY_MEDIA"] = f"@path {root / 'media'}"
            os.environ["MPLCONFIGDIR"] = str(root / "matplotlib")
            sys.path.insert(0, str(ROOT / "engine/src"))
            print(json.dumps(measure_sample(args.blocks, args.fanout, args.choices, root)))
    else:
        print(json.dumps(run(args.presets, args.samples, args.choices, args.fanout), indent=2))


if __name__ == "__main__":
    main()
