"""Backend-emitted widget-contract diagnostics."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from tangl.service.response import ProjectedState, RuntimeEnvelope


ROOT = Path(__file__).parents[3]
CONFORMANCE_DIR = ROOT / "engine" / "contrib" / "conformance"
BACKEND_DEMO_PATH = CONFORMANCE_DIR / "backend_widget_demo.py"
REFERENCE_PATH = CONFORMANCE_DIR / "reference_port.py"
DIAGNOSTIC_DIR = CONFORMANCE_DIR / "diagnostics"
RUNTIME_PATH = DIAGNOSTIC_DIR / "backend_widget_contract_runtime.json"
PROJECTED_PATH = DIAGNOSTIC_DIR / "backend_widget_contract_projected_state.json"


def _load_module(name: str, path: Path) -> ModuleType:
    module_name = f"{__name__}.{name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


BACKEND_DEMO = _load_module("backend_widget_demo", BACKEND_DEMO_PATH)
REFERENCE_PORT = _load_module("reference_port", REFERENCE_PATH)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as payload_file:
        payload = json.load(payload_file)
    assert isinstance(payload, dict)
    return payload


def test_backend_widget_diagnostics_match_generator() -> None:
    runtime_payload, projected_payload = BACKEND_DEMO.build_demo_payloads()

    assert _load_json(RUNTIME_PATH) == runtime_payload
    assert _load_json(PROJECTED_PATH) == projected_payload


def test_backend_widget_diagnostics_validate_as_service_contracts() -> None:
    runtime_payload = _load_json(RUNTIME_PATH)
    projected_payload = _load_json(PROJECTED_PATH)

    RuntimeEnvelope.model_validate(runtime_payload)
    ProjectedState.model_validate(projected_payload)

    choices = [
        fragment
        for fragment in runtime_payload["fragments"]
        if fragment.get("fragment_type") == "choice"
    ]
    assert len(choices) == 2
    assert choices[0]["uid"] != choices[0]["edge_id"]
    assert choices[0]["accepts"]["kind"] == "quantity"
    assert choices[0]["accepts"]["cost_previews"] == [
        {"ledger_key": "supplies", "delta": 1, "unit": "ration"}
    ]
    assert choices[0]["ui_hints"]["source_kind"] == "market"
    assert choices[0]["ui_hints"]["cost_previews"] == [
        {"ledger_key": "coin", "delta": -2, "unit": "silver"}
    ]
    assert choices[1]["accepts"]["kind"] == "text"
    assert runtime_payload["metadata"]["grammar"]["examples"] == [
        "Buy rations.",
        "Name the mule.",
    ]
    assert runtime_payload["metadata"]["grammar"]["verbs"] == [
        {
            "verb": "buy",
            "aliases": [],
            "frames": ["Buy rations."],
        },
        {
            "verb": "name",
            "aliases": [],
            "frames": ["Name the mule."],
        },
    ]
    assert runtime_payload["metadata"]["info_state"]["available_kinds"] == [
        "inventory",
        "map",
    ]


def test_backend_widget_diagnostics_render_in_reference_port() -> None:
    runtime_output = "\n".join(REFERENCE_PORT.render_fixture(_load_json(RUNTIME_PATH)))
    projected_output = "\n".join(REFERENCE_PORT.render_fixture(_load_json(PROJECTED_PATH)))

    assert "The road forks under cold rain." in runtime_output
    assert (
        "b) Buy rations. <quantity 1-3 ration> "
        "[cost: coin -2 silver; supplies +1 ration]"
    ) in runtime_output
    assert "n) Name the mule. <text: Buttercup>" in runtime_output
    assert "? Inventory: /info inventory (shortcuts: /i, /inv)" in runtime_output
    assert "Supplies:\n  Rations: 2" in projected_output
    assert "Mira | Scout" in projected_output
