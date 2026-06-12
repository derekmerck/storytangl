"""Tkinter reference renderer for portable conformance fixtures."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).parents[3]
FIXTURE_DIR = ROOT / "engine" / "contrib" / "conformance" / "fixtures"
PROPOSAL_DIR = ROOT / "engine" / "contrib" / "conformance" / "proposals"
TK_PATH = ROOT / "engine" / "contrib" / "conformance" / "tk_reference_port.py"


def _load_port() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tk_reference_port", TK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PORT = _load_port()


def _plans(name: str) -> tuple[object, ...]:
    _, plans = PORT.load_fixture_plan(FIXTURE_DIR / name)
    return plans


def _proposal_plans(name: str) -> tuple[object, ...]:
    _, plans = PORT.load_fixture_plan(PROPOSAL_DIR / name)
    return plans


def _choices(name: str) -> dict[str, object]:
    return {plan.text: plan for plan in _plans(name) if plan.choice is not None}


def _proposal_choices(name: str) -> dict[str, object]:
    return {plan.text: plan for plan in _proposal_plans(name) if plan.choice is not None}


def test_tk_reference_port_stays_json_only_and_uses_generic_model() -> None:
    source = TK_PATH.read_text(encoding="utf-8")

    assert "from tangl" not in source
    assert "import tangl" not in source
    assert "service_manager" not in source
    assert "cli_reference_port" not in source
    assert "render_fixture_document = _REFERENCE_PORT.render_fixture_document" in source


def test_tk_plan_maps_render_roles_to_observable_widgets() -> None:
    plans = _plans("crossroads_inn.json")
    widgets_by_role = {plan.role: plan.widget for plan in plans}

    assert widgets_by_role["content"] == "text"
    assert widgets_by_role["attributed"] == "label"
    assert widgets_by_role["media"] == "media_placeholder"
    assert widgets_by_role["fact"] == "label"
    assert widgets_by_role["ux_event"] == "label"


def test_tk_plan_renders_projected_state_sections_and_values() -> None:
    plans = _plans("projected_state_all_values.json")

    section_titles = [plan.text for plan in plans if plan.role == "projected_section"]
    values = [plan.text for plan in plans if plan.role == "projected_value"]

    assert section_titles == ["Wounds:", "Purse:", "Satchel:", "Party:", "Conditions:"]
    assert "Sound" in values
    assert "silver: 63" in values
    assert "name | role | mood" in values
    assert "rain-soaked, hungry, hunted" in values


def test_tk_choice_plan_uses_expected_controls_for_accepts_kinds() -> None:
    choices = _choices("sandbox_payload.json")
    compose_choice = _choices("compose_payload.json")["Give coins."]

    assert choices["Look around."].widget == "button"
    assert choices["Take something."].widget == "piece_selector"
    assert choices["Name your sword."].widget == "entry"
    assert choices["Offer coins."].widget == "spinbox"
    assert choices["Offer coins."].input.minimum == 1
    assert choices["Offer coins."].input.maximum == 7
    assert choices["Offer coins."].input.unit == "coin"
    assert compose_choice.widget == "compose_form"
    assert [part.role for part in compose_choice.input.parts] == ["amount", "target"]


def test_tk_piece_selector_uses_visible_pieces_from_referenced_zone() -> None:
    choice = _choices("sandbox_payload.json")["Take something."]

    assert [option.label for option in choice.input.options] == [
        "brass lamp",
        "small mailbox",
    ]
    assert [option.value for option in choice.input.options] == ["lamp", "mailbox"]

    submission = PORT.collect_submission(choice, ["lamp"])

    assert submission.as_transport() == {
        "edge_id": "00000000-0000-4000-8000-000000001507",
        "choice_uid": "00000000-0000-4000-8000-000000000507",
        "payload": {"piece_ids": ["lamp"]},
    }


def test_tk_piece_selector_accepts_top_level_target_zone_ref() -> None:
    document = PORT.render_fixture_document(
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
                    "member_ids": ["lamp-fragment"],
                    "hints": {"label_text": "Here"},
                },
                {
                    "uid": "lamp-fragment",
                    "fragment_type": "piece",
                    "piece_id": "lamp",
                    "content": "brass lamp",
                    "zone_ref": "zone",
                },
                    {
                        "uid": "choice",
                        "fragment_type": "choice",
                        "edge_id": "00000000-0000-4000-8000-000000000001",
                        "text": "Take something.",
                    "accepts": {"kind": "pieces", "target_zone_ref": "zone"},
                },
            ],
        }
    )
    choice = next(plan for plan in PORT.build_widget_plan(document) if plan.choice is not None)

    assert [option.value for option in choice.input.options] == ["lamp"]


def test_tk_place_selector_uses_visible_pieces_from_source_zone() -> None:
    choice = _proposal_choices("place_accepts.json")["Mount a weapon."]

    assert choice.widget == "place_selector"
    assert [option.label for option in choice.input.options] == ["Vulcan Gun"]

    submission = PORT.collect_submission(choice, "vulcan-1")

    assert submission.as_transport() == {
        "edge_id": "00000000-0000-4000-8000-000000013106",
        "choice_uid": "00000000-0000-4000-8000-000000013006",
        "payload": {
            "piece_id": "vulcan-1",
            "source_zone_ref": "00000000-0000-4000-8000-000000013003",
            "target_zone_ref": "00000000-0000-4000-8000-000000013005",
        },
    }


def test_tk_submission_payload_shapes_match_accepts_kinds() -> None:
    sandbox_choices = _choices("sandbox_payload.json")
    compose_choices = _choices("compose_payload.json")

    assert PORT.collect_submission(sandbox_choices["Look around."]).payload == {}
    assert PORT.collect_submission(sandbox_choices["Name your sword."], "Aster").payload == {
        "text": "Aster"
    }
    assert PORT.collect_submission(sandbox_choices["Offer coins."], 3).payload == {
        "quantity": 3
    }
    assert PORT.collect_submission(
        compose_choices["Give coins."],
        {"amount": 2, "target": ["guard"]},
    ).payload == {
        "parts": {
            "amount": {"quantity": 2},
            "target": {"piece_ids": ["guard"]},
        }
    }


def test_tk_locked_choices_are_disabled_and_non_submitting() -> None:
    choice = _choices("crossroads_inn.json")["Lift the map while he drinks."]

    assert choice.enabled is False
    assert choice.widget == "button"
    assert choice.choice is not None
    assert choice.choice.blockers == ("Sleight of Hand 1, need 2.",)

    with pytest.raises(ValueError, match="locked"):
        PORT.collect_submission(choice)


def test_tk_inspection_exposes_choice_decision_details() -> None:
    inspection = PORT.inspect_fixture(FIXTURE_DIR / "crossroads_inn.json")
    choices = {
        widget["text"]: widget
        for widget in inspection["widgets"]
        if widget["role"] == "choice"
    }

    assert choices["Pay the forty silver."]["cost_previews"] == ["purse -40 silver"]
    assert choices["Lift the map while he drinks."]["blockers"] == [
        "Sleight of Hand 1, need 2."
    ]


def test_tk_inspection_harness_loads_every_fixture_without_tkinter() -> None:
    inspections = [
        PORT.inspect_fixture(path)
        for path in sorted(FIXTURE_DIR.glob("*.json"))
    ]

    assert all(inspection["widgets"] for inspection in inspections)
    assert any(
        submission["payload"] == {"quantity": 1}
        for inspection in inspections
        for submission in inspection["sample_submissions"]
    )


def test_tk_inspection_harness_loads_every_proposal_without_tkinter() -> None:
    inspections = [
        PORT.inspect_fixture(path)
        for path in sorted(PROPOSAL_DIR.glob("*.json"))
    ]

    assert all(inspection["widgets"] for inspection in inspections)
    assert any(
        widget["role"] == "ux_event"
        for inspection in inspections
        for widget in inspection["widgets"]
    )


def test_tk_plan_keeps_unknown_fragment_fallback_observable() -> None:
    document = PORT.render_fixture_document(
        {
            "cursor_id": "fixture",
            "step": 1,
            "fragments": [
                {
                    "uid": "scene",
                    "fragment_type": "group",
                    "group_type": "scene",
                    "member_ids": ["future"],
                },
                {
                    "uid": "future",
                    "fragment_type": "future_widget",
                    "label": "Future widget",
                },
            ],
        }
    )

    plans = PORT.build_widget_plan(document)

    assert any(
        plan.role == "fallback" and plan.text == "[unsupported future_widget] Future widget"
        for plan in plans
    )
