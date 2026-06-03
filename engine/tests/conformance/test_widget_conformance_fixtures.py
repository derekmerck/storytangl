"""Portable widget conformance fixtures.

These tests keep the first JSON fixture suite loadable and mechanically useful
without pretending that every target in the widget vocabulary is implemented in
the engine today.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

import pytest

from tangl.service.response import ProjectedState, RuntimeEnvelope


FIXTURE_DIR = Path(__file__).parents[2] / "contrib" / "conformance" / "fixtures"
PROPOSAL_DIR = Path(__file__).parents[2] / "contrib" / "conformance" / "proposals"
LEGIBILITY_PATH = Path(__file__).parents[2] / "contrib" / "conformance" / "legibility.py"
PARITY_PATH = Path(__file__).parents[2] / "contrib" / "conformance" / "parity.py"
TIME_PARITY_PATH = Path(__file__).parents[2] / "contrib" / "conformance" / "time_parity.py"
PROJECTED_STATE_FIXTURE = "projected_state_all_values.json"
EXPECTED_FIXTURES = {
    "command_hints.json",
    "compose_payload.json",
    "control_delete.json",
    "credentials_shift.json",
    "crossroads_inn.json",
    "dialog_with_avatar.json",
    "pending_media_update.json",
    "projected_state_all_values.json",
    "quantity_payload.json",
    "sandbox_payload.json",
    "sandbox_info_channels.json",
}
EXPECTED_PROPOSALS = {
    "carwars_garage_turn.json",
    "piece_realization.json",
    "place_accepts.json",
    "record_kvrow.json",
    "roll_fragment.json",
    "wireframe_v15_interpretation_samples.json",
}


def _load_module(name: str, path: Path) -> ModuleType:
    module_name = f"{__name__}.{name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


LEGIBILITY = _load_module("legibility", LEGIBILITY_PATH)
PARITY = _load_module("parity", PARITY_PATH)
TIME_PARITY = _load_module("time_parity", TIME_PARITY_PATH)


def _load_fixture(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fixture_file:
        payload = json.load(fixture_file)
    assert isinstance(payload, dict), f"{path.name} must contain a JSON object"
    return payload


def _runtime_fixture_paths() -> list[Path]:
    return sorted(
        path
        for path in FIXTURE_DIR.glob("*.json")
        if path.name != PROJECTED_STATE_FIXTURE
    )


def _proposal_fixture_paths() -> list[Path]:
    return sorted(PROPOSAL_DIR.glob("*.json"))


def _fragment_uid(fragment: dict[str, Any]) -> str:
    uid = fragment.get("uid")
    assert isinstance(uid, str) and uid, "fragment uid must be a non-empty string"
    return uid


def _fragment_type(fragment: dict[str, Any]) -> str:
    fragment_type = fragment.get("fragment_type")
    assert isinstance(fragment_type, str) and fragment_type
    return fragment_type


def _registry_after_controls(fragments: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for fragment in fragments:
        fragment_type = _fragment_type(fragment)
        if fragment_type == "delete":
            ref_id = fragment.get("ref_id") or fragment.get("reference_id")
            if isinstance(ref_id, str):
                registry.pop(ref_id, None)
            continue
        if fragment_type == "update":
            ref_id = fragment.get("ref_id") or fragment.get("reference_id")
            payload = fragment.get("payload")
            if isinstance(ref_id, str) and isinstance(payload, dict):
                existing = registry.get(ref_id, {"uid": ref_id})
                registry[ref_id] = {**existing, **payload, "uid": ref_id}
            continue
        registry[_fragment_uid(fragment)] = fragment
    return registry


def _assert_fragment_shape(fragment: dict[str, Any]) -> None:
    fragment_type = _fragment_type(fragment)

    if fragment_type == "content":
        assert "content" in fragment
    elif fragment_type in {"group", "dialog"}:
        assert isinstance(fragment.get("member_ids"), list)
    elif fragment_type == "attributed":
        assert isinstance(fragment.get("who"), str)
        assert isinstance(fragment.get("content"), str)
    elif fragment_type == "media":
        assert "content" in fragment
        assert isinstance(fragment.get("content_format"), str)
    elif fragment_type == "kv":
        rows = fragment.get("content")
        assert isinstance(rows, list)
        assert all(
            isinstance(row, dict) and isinstance(row.get("key"), str) and "value" in row
            for row in rows
        )
    elif fragment_type == "choice":
        assert isinstance(fragment.get("text"), str)
        accepts = fragment.get("accepts")
        assert accepts is None or isinstance(accepts, dict)
    elif fragment_type in {"update", "delete"}:
        assert isinstance(fragment.get("ref_id") or fragment.get("reference_id"), str)
        if fragment_type == "update":
            assert isinstance(fragment.get("payload"), dict)
    elif fragment_type == "user_event":
        assert "content" in fragment
    elif fragment_type == "piece":
        assert isinstance(fragment.get("piece_id"), str)
    elif fragment_type == "interpretation":
        assert isinstance(fragment.get("message") or fragment.get("content"), str)
        result = fragment.get("result")
        text = fragment.get("text")
        assert result is None or isinstance(result, str)
        assert text is None or isinstance(text, str)
    else:
        pytest.fail(f"Fixture uses unexpected fragment type {fragment_type!r}")


def test_expected_fixture_suite_is_present() -> None:
    assert {path.name for path in FIXTURE_DIR.glob("*.json")} == EXPECTED_FIXTURES


def test_expected_proposal_fixture_suite_is_present_but_not_gating() -> None:
    assert {path.name for path in _proposal_fixture_paths()} == EXPECTED_PROPOSALS
    assert not (EXPECTED_FIXTURES & EXPECTED_PROPOSALS)


@pytest.mark.parametrize("path", _runtime_fixture_paths(), ids=lambda path: path.name)
def test_runtime_fixtures_validate_as_runtime_envelopes(path: Path) -> None:
    payload = _load_fixture(path)

    RuntimeEnvelope.model_validate(payload)


@pytest.mark.parametrize("path", _proposal_fixture_paths(), ids=lambda path: path.name)
def test_proposal_fixtures_are_loadable_runtime_envelopes(path: Path) -> None:
    payload = _load_fixture(path)

    assert payload.get("metadata", {}).get("proposal") is True
    RuntimeEnvelope.model_validate(payload)


def test_projected_state_fixture_validates_all_section_value_types() -> None:
    payload = _load_fixture(FIXTURE_DIR / PROJECTED_STATE_FIXTURE)

    state = ProjectedState.model_validate(payload)

    assert [section.value.value_type for section in state.sections] == [
        "scalar",
        "kv_list",
        "item_list",
        "table",
        "badges",
    ]


@pytest.mark.parametrize("path", _runtime_fixture_paths(), ids=lambda path: path.name)
def test_runtime_fixtures_have_portable_fragment_shapes(path: Path) -> None:
    payload = _load_fixture(path)
    fragments = payload.get("fragments")
    assert isinstance(fragments, list) and fragments

    seen: set[str] = set()
    for fragment in fragments:
        assert isinstance(fragment, dict)
        uid = _fragment_uid(fragment)
        assert uid not in seen, f"{path.name} repeats uid {uid}"
        seen.add(uid)
        _assert_fragment_shape(fragment)


@pytest.mark.parametrize("path", _runtime_fixture_paths(), ids=lambda path: path.name)
def test_runtime_fixtures_pass_decision_legibility(path: Path) -> None:
    payload = _load_fixture(path)

    result = LEGIBILITY.check_runtime_envelope(payload)

    LEGIBILITY.assert_no_issues(result.issues)


@pytest.mark.parametrize("path", _runtime_fixture_paths(), ids=lambda path: path.name)
def test_runtime_fixtures_pass_input_parity(path: Path) -> None:
    payload = _load_fixture(path)

    result = PARITY.check_runtime_envelope(payload)

    PARITY.assert_no_issues(result.issues)


@pytest.mark.parametrize("path", _runtime_fixture_paths(), ids=lambda path: path.name)
def test_runtime_fixtures_pass_time_parity(path: Path) -> None:
    payload = _load_fixture(path)

    result = TIME_PARITY.check_runtime_envelope(payload)

    TIME_PARITY.assert_no_issues(result.issues)


def test_decision_legibility_reports_hidden_choice_references() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["choice"],
            },
            {
                "uid": "hidden-zone",
                "fragment_type": "group",
                "group_type": "zone",
                "member_ids": [],
            },
            {
                "uid": "choice",
                "fragment_type": "choice",
                "text": "Take one.",
                "available": True,
                "accepts": {
                    "kind": "pieces",
                    "constraints": {"target_zone_ref": "hidden-zone"},
                },
            },
        ],
    }

    result = LEGIBILITY.check_runtime_envelope(payload)

    assert [issue.ref_id for issue in result.issues] == ["hidden-zone"]
    assert result.issues[0].choice_uid == "choice"
    assert result.issues[0].reason == "referenced state is not renderable"


def test_decision_legibility_accepts_visible_piece_domain_ids() -> None:
    payload = {
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
                "member_ids": ["piece-fragment"],
            },
            {
                "uid": "piece-fragment",
                "fragment_type": "piece",
                "piece_id": "lamp",
            },
            {
                "uid": "choice",
                "fragment_type": "choice",
                "text": "Use the lamp.",
                "available": True,
                "accepts": {
                    "kind": "pieces",
                    "piece_ids": ["lamp"],
                },
            },
        ],
    }

    result = LEGIBILITY.check_runtime_envelope(payload)

    assert result.issues == ()


def test_decision_legibility_reports_blocker_refs() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["choice"],
            },
            {
                "uid": "choice",
                "fragment_type": "choice",
                "text": "Unlock it.",
                "available": True,
                "blockers": [
                    {
                        "code": "missing_key",
                        "message": "Needs the brass key.",
                        "refs": ["hidden-key"],
                    }
                ],
            },
        ],
    }

    result = LEGIBILITY.check_runtime_envelope(payload)

    assert [issue.ref_id for issue in result.issues] == ["hidden-key"]


def test_decision_legibility_reports_place_edge_refs() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["zone", "piece", "choice"],
            },
            {
                "uid": "zone",
                "fragment_type": "group",
                "group_type": "zone",
                "zone_id": "inventory",
                "member_ids": ["piece"],
            },
            {
                "uid": "piece",
                "fragment_type": "piece",
                "piece_id": "lamp",
            },
            {
                "uid": "choice",
                "fragment_type": "choice",
                "text": "Move the lamp.",
                "available": True,
                "accepts": {
                    "kind": "place",
                    "source_zone_ref": "inventory",
                    "edge_ref": "hidden-exit",
                },
            },
        ],
    }

    result = LEGIBILITY.check_runtime_envelope(payload)

    assert [issue.ref_id for issue in result.issues] == ["hidden-exit"]


def test_input_parity_reports_unsubmittable_piece_choices() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["choice"],
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
                "text": "Take one.",
                "available": True,
                "accepts": {
                    "kind": "pieces",
                    "min": 1,
                    "constraints": {"target_zone_ref": "zone"},
                },
            },
        ],
    }

    result = PARITY.check_runtime_envelope(payload)

    assert [issue.reason for issue in result.issues] == [
        "target zone 'zone' is not renderable",
    ]


def test_input_parity_reports_invalid_compose_parts() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["choice"],
            },
            {
                "uid": "choice",
                "fragment_type": "choice",
                "text": "Give something.",
                "available": True,
                "accepts": {
                    "kind": "compose",
                    "parts": [
                        {"role": "amount", "accepts": {"kind": "quantity", "min": 5, "max": 1}},
                        {"role": "amount", "accepts": {"kind": "text"}},
                        {"accepts": {"kind": "unknown"}},
                    ],
                },
            },
        ],
    }

    result = PARITY.check_runtime_envelope(payload)

    assert [issue.reason for issue in result.issues] == [
        "`min` exceeds `max`",
        "duplicate role 'amount'",
        "missing role",
        "missing or unsupported accepts kind",
    ]


def test_input_parity_reports_negative_bounds() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["zone", "piece", "choice"],
            },
            {
                "uid": "zone",
                "fragment_type": "group",
                "group_type": "zone",
                "zone_id": "inventory",
                "member_ids": ["piece"],
            },
            {
                "uid": "piece",
                "fragment_type": "piece",
                "piece_id": "lamp",
            },
            {
                "uid": "choice",
                "fragment_type": "choice",
                "text": "Give supplies.",
                "available": True,
                "accepts": {
                    "kind": "compose",
                    "parts": [
                        {"role": "amount", "accepts": {"kind": "quantity", "min": -1}},
                        {
                            "role": "item",
                            "accepts": {
                                "kind": "pieces",
                                "target_zone_ref": "inventory",
                                "max": -1,
                            },
                        },
                    ],
                },
            },
        ],
    }

    result = PARITY.check_runtime_envelope(payload)

    assert [issue.reason for issue in result.issues] == [
        "`min` must be non-negative",
        "`max` must be non-negative",
    ]


def test_time_parity_reports_unreadable_pending_media() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["media"],
            },
            {
                "uid": "media",
                "fragment_type": "media",
                "content": "",
                "content_format": "rit",
                "generation_status": "ready",
            },
        ],
    }

    result = TIME_PARITY.check_runtime_envelope(payload)

    assert [issue.reason for issue in result.issues] == [
        "media is missing readable content",
        "ready media must resolve beyond rit",
    ]


@pytest.mark.parametrize("content", [{}, []], ids=["empty-object", "empty-list"])
def test_time_parity_reports_empty_container_fallbacks(content: Any) -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["media"],
            },
            {
                "uid": "media",
                "fragment_type": "media",
                "content": content,
                "content_format": "url",
            },
        ],
    }

    result = TIME_PARITY.check_runtime_envelope(payload)

    assert [issue.reason for issue in result.issues] == [
        "media is missing readable content",
    ]


def test_time_parity_accepts_roll_proposal_fallback() -> None:
    payload = _load_fixture(PROPOSAL_DIR / "roll_fragment.json")

    result = TIME_PARITY.check_runtime_envelope(payload)

    TIME_PARITY.assert_no_issues(result.issues)


def test_time_parity_reports_blocking_roll_rituals() -> None:
    payload = {
        "cursor_id": "fixture",
        "step": 1,
        "fragments": [
            {
                "uid": "scene",
                "fragment_type": "group",
                "group_type": "scene",
                "member_ids": ["roll"],
            },
            {
                "uid": "roll",
                "fragment_type": "roll",
                "label": "Fate",
                "outcome": "fail",
                "ritual_hints": {
                    "duration_ms": True,
                    "skip_label": "",
                    "requires_completion": True,
                },
            },
        ],
    }

    result = TIME_PARITY.check_runtime_envelope(payload)

    assert [issue.reason for issue in result.issues] == [
        "roll needs inputs or narrative for fallback",
        "ritual duration_ms must be a non-negative integer",
        "ritual skip_label must be readable when present",
        "timing hint 'requires_completion' cannot be true",
    ]


def test_command_hint_fixture_keeps_grammar_advisory() -> None:
    payload = _load_fixture(FIXTURE_DIR / "command_hints.json")
    grammar = payload.get("metadata", {}).get("grammar")

    assert isinstance(grammar, dict)
    assert grammar["examples"][0] == "take lamp"

    raw_command_choices = [
        fragment
        for fragment in payload["fragments"]
        if (
            isinstance(fragment, dict)
            and fragment.get("fragment_type") == "choice"
            and fragment.get("accepts", {}).get("kind") == "raw_command"
        )
    ]
    assert len(raw_command_choices) == 1
    assert raw_command_choices[0]["edge_id"] == "interpret_command"


def test_control_update_and_delete_fixtures_apply_to_registry() -> None:
    update_payload = _load_fixture(FIXTURE_DIR / "pending_media_update.json")
    update_registry = _registry_after_controls(update_payload["fragments"])
    updated_media = update_registry["00000000-0000-4000-8000-000000000302"]
    assert updated_media["content_format"] == "url"
    assert updated_media["generation_status"] == "ready"

    delete_payload = _load_fixture(FIXTURE_DIR / "control_delete.json")
    delete_registry = _registry_after_controls(delete_payload["fragments"])
    assert "00000000-0000-4000-8000-000000000702" not in delete_registry


def test_credentials_shift_fixture_round_trips_through_typed_models() -> None:
    """Pin the credentials envelope to the typed engine fragments (Bridge.1/2b)."""

    from tangl.journal.fragments import (
        ChoiceFragment,
        GroupFragment,
        KvFragment,
        PieceFragment,
    )

    payload = _load_fixture(FIXTURE_DIR / "credentials_shift.json")
    by_uid = {f["uid"]: f for f in payload["fragments"]}

    # Candidate + document pieces validate as typed PieceFragments.
    candidate = PieceFragment.model_validate(by_uid["00000000-0000-4000-8000-000000000603"])
    assert candidate.kind == "candidate"
    assert candidate.properties["declared_purpose"] == "work"

    permit = PieceFragment.model_validate(by_uid["00000000-0000-4000-8000-000000000606"])
    assert permit.kind == "permit"
    assert str(permit.zone_ref) == "00000000-0000-4000-8000-000000000604"

    # Packet zone validates as a typed GroupFragment carrying its zone_role.
    packet = GroupFragment.model_validate(by_uid["00000000-0000-4000-8000-000000000604"])
    assert packet.group_type == "zone"
    assert packet.zone_role == "packet"
    assert permit.uid in packet.member_ids

    # Findings validate as a typed KvFragment with severity emphasis.
    findings = KvFragment.model_validate(by_uid["00000000-0000-4000-8000-000000000607"])
    emphases = {row.key: row.emphasis for row in findings.content}
    assert emphases["work permit"] == "warn"
    assert emphases["packet consistency"] == "danger"

    # Choices validate as typed ChoiceFragments -- proving the edge_ids are
    # real UUIDs that round-trip through the service/client typed path, not
    # loose semantic strings the typed decoder would reject.
    choices = [
        ChoiceFragment.model_validate(f)
        for f in payload["fragments"]
        if f.get("fragment_type") == "choice"
    ]
    assert all(isinstance(c.edge_id, UUID) for c in choices)

    # Disclosure discipline: every plausible mediation is offered uniformly and
    # no disposition is pre-gated by the answer, so the menu reveals nothing
    # about which call is correct or which mediation is useful. (Choices are
    # identified by display text; edge_ids are opaque to the client.)
    texts = {c.text for c in choices}
    assert {"Request reissue of work permit.", "Verify identity.", "Request search."} <= texts
    dispositions = [c for c in choices if c.text.startswith("Choose ")]
    assert dispositions and all(c.available is not False for c in dispositions)

    advertised = {a["kind"] for a in payload["metadata"]["info_affordances"]}
    assert advertised == {"rules", "roster_progress", "case_summary"}
