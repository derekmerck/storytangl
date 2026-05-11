"""Terminal reference renderer for portable conformance fixtures."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).parents[3]
FIXTURE_DIR = ROOT / "engine" / "contrib" / "conformance" / "fixtures"
REFERENCE_PATH = ROOT / "engine" / "contrib" / "conformance" / "reference_port.py"
CLI_PATH = ROOT / "engine" / "contrib" / "conformance" / "cli_reference_port.py"


def _load_port() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reference_port", REFERENCE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PORT = _load_port()


def _render(name: str) -> str:
    payload = PORT.load_fixture(FIXTURE_DIR / name)
    return "\n".join(PORT.render_fixture(payload))


def test_cli_reference_port_stays_json_only() -> None:
    source = REFERENCE_PATH.read_text(encoding="utf-8")

    assert "from tangl" not in source
    assert "import tangl" not in source


def test_cli_script_is_a_thin_adapter_over_the_generic_reference_port() -> None:
    source = CLI_PATH.read_text(encoding="utf-8")

    assert "render_fixture_document = _REFERENCE_PORT.render_fixture_document" in source
    assert "from tangl" not in source
    assert "import tangl" not in source


def test_generic_reference_model_exposes_roles_and_choice_controls() -> None:
    payload = PORT.load_fixture(FIXTURE_DIR / "sandbox_payload.json")
    document = PORT.render_fixture_document(payload)

    zone = next(item for item in document.items if item.role == "zone_label")
    pieces = [item for item in document.items if item.role == "piece"]
    choices = {choice.label: choice for choice in document.choices}

    assert document.kind == "runtime_envelope"
    assert zone.text == "Here:"
    assert [piece.text for piece in pieces] == [
        "- brass lamp [available]",
        "- small mailbox [closed]",
    ]
    assert choices["Take something."].accepts_kind == "pieces"
    assert choices["Take something."].prompt == " <select 1 piece from Here>"
    assert choices["Name your sword."].accepts_kind == "text"
    assert choices["Offer coins."].accepts_kind == "quantity"


def test_cli_reference_renders_story_flow_choices_and_events() -> None:
    output = _render("crossroads_inn.json")

    assert "Rain drums on the thatch." in output
    assert "Stranger [low, confidential]: They say you're headed north." in output
    assert "1) Pay the forty silver." in output
    assert "x) Lift the map while he drinks. [locked: Requires Sleight of Hand >= 2]" in output
    assert '[event:achievement_progress] {"id": "met_10_strangers", "progress": "7/10"}' in output


def test_cli_reference_renders_piece_zone_and_payload_prompts() -> None:
    output = _render("sandbox_payload.json")

    assert "Here:" in output
    assert "- brass lamp [available]" in output
    assert "- small mailbox [closed]" in output
    assert "2) Take something. <select 1 piece from Here>" in output
    assert "3) Name your sword. <text: e.g. Hopebreaker>" in output
    assert "4) Offer coins. <quantity 1-7 coin>" in output


def test_cli_reference_renders_command_hints_as_advisory_prompt() -> None:
    output = _render("command_hints.json")

    assert "[interpretation:impossible]" in output
    assert "You can't eat the mailbox." in output
    assert ">) Try a command. <command: e.g. take lamp>" in output


def test_cli_reference_renders_projected_state_value_types() -> None:
    output = _render("projected_state_all_values.json")

    assert "Wounds:\n  Sound" in output
    assert "Purse:\n  silver: 63" in output
    assert "Hooded lantern: half-oil | light" in output
    assert "name | role | mood" in output
    assert "Bram | soldier | surly" in output
    assert "Conditions:\n  rain-soaked, hungry, hunted" in output


def test_cli_reference_applies_control_update_and_delete_before_rendering() -> None:
    update_output = _render("pending_media_update.json")
    delete_output = _render("control_delete.json")

    assert "/media/world/tangl_world/vellum_map_close_up.svg" in update_output
    assert "gen:vellum_map_close_up" not in update_output
    assert "This line is removed before rendering." not in delete_output
    assert "(empty scene)" in delete_output


def test_cli_reference_keeps_unknown_fragment_fallback_observable() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["unknown"],
            },
            {
                "uid": "unknown",
                "fragment_type": "mystery",
                "label": "Future widget",
            },
        ],
    }

    output = "\n".join(PORT.render_fixture(payload))

    assert "[unsupported mystery] Future widget" in output
