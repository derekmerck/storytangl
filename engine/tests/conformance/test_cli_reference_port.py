"""Terminal reference renderer for portable conformance fixtures."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).parents[3]
FIXTURE_DIR = ROOT / "engine" / "contrib" / "conformance" / "fixtures"
PROPOSAL_DIR = ROOT / "engine" / "contrib" / "conformance" / "proposals"
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


def _render_proposal(name: str) -> str:
    payload = PORT.load_fixture(PROPOSAL_DIR / name)
    return "\n".join(PORT.render_fixture(payload))


def _available_info_affordances(payload: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = payload.get("metadata")
    assert isinstance(metadata, dict)
    affordances = metadata.get("info_affordances")
    assert isinstance(affordances, list)
    info_state = metadata.get("info_state")
    if not isinstance(info_state, dict) or "available_kinds" not in info_state:
        return [item for item in affordances if isinstance(item, dict)]

    available_kinds = info_state.get("available_kinds")
    assert isinstance(available_kinds, list)
    return [
        item
        for item in affordances
        if isinstance(item, dict) and (item.get("kind") or "info") in available_kinds
    ]


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
    assert "1) Pay the forty silver. [cost: purse -40 silver]" in output
    assert (
        "x) Lift the map while he drinks. "
        "[locked: Requires Sleight of Hand >= 2] "
        "[blockers: Sleight of Hand 1, need 2.]"
        in output
    )
    assert "[interrupt:success:achievement_progress] Met 7 of 10 strangers." in output


def test_cli_reference_renders_piece_zone_and_payload_prompts() -> None:
    output = _render("sandbox_payload.json")
    compose_output = _render("compose_payload.json")

    assert "Here:" in output
    assert "- brass lamp [available]" in output
    assert "- small mailbox [closed]" in output
    assert "2) Take something. <select 1 piece from Here>" in output
    assert "3) Name your sword. <text: e.g. Hopebreaker>" in output
    assert "4) Offer coins. <quantity 1-7 coin>" in output
    assert "1) Give coins. <compose: amount, target>" in compose_output


def test_cli_reference_renders_command_hints_as_advisory_prompt() -> None:
    output = _render("command_hints.json")

    assert "> Command: e.g. take lamp" in output
    assert "[inline:warning:edge_rejected]" in output
    assert "You can't eat the mailbox. The mailbox is fixed to the wall." in output


def test_cli_reference_renders_info_affordances_as_queryable_commands() -> None:
    sandbox_output = _render("sandbox_info_channels.json")
    credentials_output = _render("credentials_shift.json")

    assert "Story info:" in sandbox_output
    assert "? Map: /info map (shortcuts: /m, /map) query=" in sandbox_output
    assert '"scope": "known"' in sandbox_output
    assert "? Today's rules: /info rules (shortcuts: /r, /rules)" in credentials_output
    assert "? Shift progress: /info roster_progress (shortcuts: /p, /shift)" in credentials_output
    assert "? Findings: /info case_summary (shortcuts: /c, /findings)" in credentials_output


def test_cli_reference_makes_every_available_info_affordance_reachable() -> None:
    for name in ("sandbox_info_channels.json", "credentials_shift.json"):
        payload = PORT.load_fixture(FIXTURE_DIR / name)
        document = PORT.render_fixture_document(payload)
        floor_items = {
            item.data["kind"]: item
            for item in document.items
            if item.role == "info_affordance" and item.data is not None
        }
        advertised = _available_info_affordances(payload)

        assert set(floor_items) == {str(item["kind"]) for item in advertised}
        for affordance in advertised:
            kind = str(affordance["kind"])
            item = floor_items[kind]
            commands = item.data["commands"]
            assert f"/info {kind}" in commands
            assert f"/info {kind}" in item.text
            assert item.data["query"] == affordance.get("query")
            for shortcut in affordance.get("shortcuts", []):
                assert f"/{shortcut}" in commands
                assert f"/{shortcut}" in item.text


def test_cli_reference_hides_unavailable_info_affordances() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": [],
            }
        ],
        "metadata": {
            "info_affordances": [
                {"kind": "map", "label": "Map", "shortcuts": ["m"]},
                {"kind": "inventory", "label": "Carrying", "shortcuts": ["i"]},
            ],
            "info_state": {
                "version": 1,
                "dirty_kinds": ["map"],
                "available_kinds": ["map"],
            },
        },
    }

    document = PORT.render_fixture_document(payload)
    visible_kinds = [
        item.data["kind"]
        for item in document.items
        if item.role == "info_affordance" and item.data is not None
    ]

    assert visible_kinds == ["map"]


def test_cli_reference_renders_projected_state_value_types() -> None:
    payload = PORT.load_fixture(FIXTURE_DIR / "projected_state_all_values.json")
    document = PORT.render_fixture_document(payload)
    output = "\n".join(PORT.format_document(document))

    assert "Wounds:\n  Sound" in output
    assert "Purse:\n  silver: 63" in output
    assert "Hooded lantern: half-oil | light" in output
    assert "name | role | mood" in output
    assert "Bram | soldier | surly" in output
    assert "Conditions:\n  rain-soaked, hungry, hunted" in output
    assert all(
        item.ref_id == "party"
        for item in document.items
        if item.role == "projected_value" and item.text in {"Bram | soldier | surly", "Elen | scout | watchful"}
    )


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


def test_cli_reference_can_inspect_proposal_fixtures_without_promoting_them() -> None:
    garage_output = _render_proposal("carwars_garage_turn.json")
    roll_output = _render_proposal("roll_fragment.json")
    kv_output = _render_proposal("record_kvrow.json")
    ux_event_output = _render_proposal("wireframe_v15_ux_event_samples.json")

    assert "1) Mount a weapon. <place from parts on hand to turret>" in garage_output
    assert "2) Buy from Murph's. <select 0-2 pieces from Murph's wares>" in garage_output
    assert "- Flamethrower [offer]" in garage_output
    assert "- Rocket Launcher Mk II [offer, locked: Out of stock until next session.]" in garage_output
    assert "[roll:dice] Driving check: 2d6 rolled 4 + 5 = 9 vs 12 outcome=fail." in roll_output
    assert "Fuel: 6" in kv_output
    assert "[inline:warning:edge_ambiguous] Which key: brass or iron?" in ux_event_output
    assert "[inline:warning:edge_rejected] The hatch is bolted from above." in ux_event_output
