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
EXPECTED_SEQUENCES = {"garage_buy_mount.json"}

SCENE_ID = "00000000-0000-4000-8000-000000021001"
MEDIA_ID = "00000000-0000-4000-8000-000000021003"
CATALOG_ID = "00000000-0000-4000-8000-000000021004"
LOOSE_ID = "00000000-0000-4000-8000-000000021006"
FRONT_ID = "00000000-0000-4000-8000-000000021007"
CUSTOM_ID = "00000000-0000-4000-8000-000000021009"
FLAME_ID = "00000000-0000-4000-8000-000000021013"


def _load_port() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reference_port", REFERENCE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PORT = _load_port()


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
    assert "1) Mount the flamethrower. <place from parts on hand to front mount>" in _lines(steps[1])
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

    for step in PORT.render_sequence_steps(sequence):
        visible = _visible_ids_from_scene(step.registry, SCENE_ID)
        for choice in step.document.choices:
            if not choice.available or choice.accepts is None:
                continue
            refs = _collect_reference_ids(choice.accepts)
            assert refs <= visible, f"step {step.index}: hidden refs {refs - visible}"


def _visible_ids_from_scene(registry: dict[str, dict[str, Any]], scene_id: str) -> set[str]:
    visible: set[str] = set()

    def visit(uid: str) -> None:
        if uid in visible:
            return
        visible.add(uid)
        fragment = registry.get(uid)
        if fragment is None or fragment.get("fragment_type") != "group":
            return
        member_ids = fragment.get("member_ids", [])
        assert isinstance(member_ids, list)
        for member_id in member_ids:
            if isinstance(member_id, str):
                visit(member_id)

    visit(scene_id)
    return visible


def _collect_reference_ids(value: object, parent_key: str = "") -> set[str]:
    if isinstance(value, str):
        return {value} if parent_key.endswith(("_ref", "_id")) else set()
    if isinstance(value, list):
        return {ref for item in value for ref in _collect_reference_ids(item, parent_key)}
    if not isinstance(value, dict):
        return set()

    refs: set[str] = set()
    for key, item in value.items():
        if key.endswith(("_refs", "_ids")) and isinstance(item, list):
            refs.update(entry for entry in item if isinstance(entry, str))
            continue
        refs.update(_collect_reference_ids(item, key))
    return refs
