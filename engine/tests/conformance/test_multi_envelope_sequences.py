"""Multi-envelope conformance sequence fixtures."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from tangl.service.response import RuntimeEnvelope


ROOT = Path(__file__).parents[3]
SEQUENCE_DIR = ROOT / "engine" / "contrib" / "conformance" / "sequences"
REFERENCE_PATH = ROOT / "engine" / "contrib" / "conformance" / "reference_port.py"
LEGIBILITY_PATH = ROOT / "engine" / "contrib" / "conformance" / "legibility.py"
PARITY_PATH = ROOT / "engine" / "contrib" / "conformance" / "parity.py"
TIME_PARITY_PATH = ROOT / "engine" / "contrib" / "conformance" / "time_parity.py"
EXPECTED_SEQUENCES = {"garage_buy_mount.json"}

MEDIA_ID = "00000000-0000-4000-8000-000000021003"
CATALOG_ID = "00000000-0000-4000-8000-000000021004"
LOOSE_ID = "00000000-0000-4000-8000-000000021006"
FRONT_ID = "00000000-0000-4000-8000-000000021007"
CUSTOM_ID = "00000000-0000-4000-8000-000000021009"
FLAME_ID = "00000000-0000-4000-8000-000000021013"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PORT = _load_module("reference_port", REFERENCE_PATH)
LEGIBILITY = _load_module("legibility", LEGIBILITY_PATH)
PARITY = _load_module("parity", PARITY_PATH)
TIME_PARITY = _load_module("time_parity", TIME_PARITY_PATH)


def _load_sequence(name: str) -> dict[str, Any]:
    with (SEQUENCE_DIR / name).open(encoding="utf-8") as sequence_file:
        payload = json.load(sequence_file)
    assert isinstance(payload, dict)
    return payload


def _lines(step: Any) -> str:
    return "\n".join(step.lines)


def test_expected_sequence_fixture_suite_is_present() -> None:
    assert {path.name for path in SEQUENCE_DIR.glob("*.json")} == EXPECTED_SEQUENCES


def test_sequence_envelopes_validate_as_runtime_envelopes() -> None:
    sequence = _load_sequence("garage_buy_mount.json")
    envelopes = sequence.get("envelopes")
    assert isinstance(envelopes, list)

    for envelope in envelopes:
        RuntimeEnvelope.model_validate(envelope)


def test_reference_port_applies_registry_updates_across_envelopes() -> None:
    sequence = _load_sequence("garage_buy_mount.json")

    steps = PORT.render_sequence_steps(sequence)

    assert [step.index for step in steps] == [1, 2, 3]
    assert "gen:garage-card" in _lines(steps[0])
    assert "- Flamethrower [offer]" in _lines(steps[0])
    assert "[unsupported custom_probe] debug marker" in _lines(steps[0])

    assert "/media/world/carwars/garage-card.svg" in _lines(steps[1])
    assert "gen:garage-card" not in _lines(steps[1])
    assert "Murph's wares:\n  (empty)" in _lines(steps[1])
    assert "parts on hand:\n  - Flamethrower" in _lines(steps[1])
    assert (
        "1) Mount the flamethrower. <place from parts on hand to front mount>"
        in _lines(steps[1])
    )
    assert "Buy from Murph's." not in _lines(steps[1])
    assert "[unsupported custom_probe] debug marker" in _lines(steps[1])

    assert "parts on hand:\n  (empty)" in _lines(steps[2])
    assert "front mount:\n  - Flamethrower [mounted]" in _lines(steps[2])
    assert "[unsupported custom_probe]" not in _lines(steps[2])
    assert "1) Hit the road." in _lines(steps[2])

    final_registry = steps[2].registry
    assert final_registry[MEDIA_ID]["content_format"] == "url"
    assert final_registry[CATALOG_ID]["member_ids"] == []
    assert final_registry[LOOSE_ID]["member_ids"] == []
    assert final_registry[FRONT_ID]["member_ids"] == [FLAME_ID]
    assert final_registry[FLAME_ID]["zone_ref"] == FRONT_ID
    assert CUSTOM_ID not in final_registry


def test_sequence_open_choice_references_stay_renderable() -> None:
    sequence = _load_sequence("garage_buy_mount.json")

    LEGIBILITY.assert_no_issues(LEGIBILITY.check_sequence(sequence))


def test_sequence_open_choices_keep_portable_input_shapes() -> None:
    sequence = _load_sequence("garage_buy_mount.json")

    PARITY.assert_no_issues(PARITY.check_sequence(sequence))


def test_sequence_timed_fragments_keep_portable_fallbacks() -> None:
    sequence = _load_sequence("garage_buy_mount.json")

    TIME_PARITY.assert_no_issues(TIME_PARITY.check_sequence(sequence))


def test_sequence_legibility_uses_current_registry_after_updates() -> None:
    sequence = {
        "sequence_id": "hidden_ref_after_update",
        "envelopes": [
            {
                "cursor_id": "fixture",
                "step": 1,
                "fragments": [
                    {
                        "uid": "scene",
                        "fragment_type": "group",
                        "group_type": "scene",
                        "member_ids": ["zone", "choice"],
                    },
                    {
                        "uid": "zone",
                        "fragment_type": "group",
                        "group_type": "zone",
                        "member_ids": [],
                    },
                    {
                        "uid": "choice",
                        "fragment_type": "choice",
                        "text": "Use the zone.",
                        "accepts": {
                            "kind": "pieces",
                            "constraints": {"target_zone_ref": "zone"},
                        },
                    },
                ],
            },
            {
                "cursor_id": "fixture",
                "step": 2,
                "fragments": [
                    {
                        "uid": "scene-update",
                        "fragment_type": "update",
                        "ref_id": "scene",
                        "payload": {"member_ids": ["choice"]},
                    }
                ],
            },
        ],
    }

    issues = LEGIBILITY.check_sequence(sequence)

    assert len(issues) == 1
    assert issues[0].step_index == 2
    assert issues[0].choice_uid == "choice"
    assert issues[0].ref_id == "zone"


def test_sequence_input_parity_uses_current_registry_after_updates() -> None:
    sequence = {
        "sequence_id": "empty_source_after_update",
        "envelopes": [
            {
                "cursor_id": "fixture",
                "step": 1,
                "fragments": [
                    {
                        "uid": "scene",
                        "fragment_type": "group",
                        "group_type": "scene",
                        "member_ids": ["source", "target", "piece", "choice"],
                    },
                    {
                        "uid": "source",
                        "fragment_type": "group",
                        "group_type": "zone",
                        "member_ids": ["piece"],
                    },
                    {
                        "uid": "target",
                        "fragment_type": "group",
                        "group_type": "zone",
                        "member_ids": [],
                    },
                    {
                        "uid": "piece",
                        "fragment_type": "piece",
                        "piece_id": "lamp",
                    },
                    {
                        "uid": "choice",
                        "fragment_type": "choice",
                        "text": "Move it.",
                        "accepts": {
                            "kind": "place",
                            "source_zone_ref": "source",
                            "target_zone_ref": "target",
                        },
                    },
                ],
            },
            {
                "cursor_id": "fixture",
                "step": 2,
                "fragments": [
                    {
                        "uid": "source-update",
                        "fragment_type": "update",
                        "ref_id": "source",
                        "payload": {"member_ids": []},
                    }
                ],
            },
        ],
    }

    issues = PARITY.check_sequence(sequence)

    assert len(issues) == 1
    assert issues[0].step_index == 2
    assert issues[0].choice_uid == "choice"
    assert issues[0].reason == "source zone 'source' has no selectable pieces"
