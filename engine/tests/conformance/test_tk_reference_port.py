"""Tkinter reference renderer for portable conformance fixtures."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).parents[3]
FIXTURE_DIR = ROOT / "engine" / "contrib" / "conformance" / "fixtures"
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


def _choices(name: str) -> dict[str, object]:
    return {plan.text: plan for plan in _plans(name) if plan.choice is not None}


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
    assert widgets_by_role["user_event"] == "label"


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

    assert choices["Look around."].widget == "button"
    assert choices["Take something."].widget == "piece_selector"
    assert choices["Name your sword."].widget == "entry"
    assert choices["Offer coins."].widget == "spinbox"
    assert choices["Offer coins."].input.minimum == 1
    assert choices["Offer coins."].input.maximum == 7
    assert choices["Offer coins."].input.unit == "coin"


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


def test_tk_submission_payload_shapes_match_accepts_kinds() -> None:
    sandbox_choices = _choices("sandbox_payload.json")
    command_choices = _choices("command_hints.json")

    assert PORT.collect_submission(sandbox_choices["Look around."]).payload == {}
    assert PORT.collect_submission(sandbox_choices["Name your sword."], "Aster").payload == {
        "text": "Aster"
    }
    assert PORT.collect_submission(sandbox_choices["Offer coins."], 3).payload == {
        "quantity": 3
    }
    assert PORT.collect_submission(command_choices["Try a command."], "take lamp").payload == {
        "text": "take lamp"
    }


def test_tk_locked_choices_are_disabled_and_non_submitting() -> None:
    choice = _choices("crossroads_inn.json")["Lift the map while he drinks."]

    assert choice.enabled is False
    assert choice.widget == "button"

    with pytest.raises(ValueError, match="locked"):
        PORT.collect_submission(choice)


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
