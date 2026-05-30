"""Portable widget conformance fixtures.

These tests keep the first JSON fixture suite loadable and mechanically useful
without pretending that every target in the widget vocabulary is implemented in
the engine today.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from tangl.service.response import ProjectedState, RuntimeEnvelope


FIXTURE_DIR = Path(__file__).parents[2] / "contrib" / "conformance" / "fixtures"
PROPOSAL_DIR = Path(__file__).parents[2] / "contrib" / "conformance" / "proposals"
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
}
EXPECTED_PROPOSALS = {
    "carwars_garage_turn.json",
    "piece_realization.json",
    "place_accepts.json",
    "record_kvrow.json",
    "roll_fragment.json",
    "wireframe_v15_interpretation_samples.json",
}


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


def _renderable_ids_by_scene(fragments: list[dict[str, Any]]) -> list[set[str]]:
    registry = _registry_after_controls(fragments)
    scenes = [
        fragment
        for fragment in registry.values()
        if fragment.get("fragment_type") == "group" and fragment.get("group_type") == "scene"
    ]

    visible_by_scene: list[set[str]] = []
    for scene in scenes:
        visible: set[str] = set()

        def visit(uid: str) -> None:
            if uid in visible:
                return
            visible.add(uid)
            fragment = registry.get(uid)
            if fragment is None:
                return
            if fragment.get("fragment_type") == "group":
                member_ids = fragment.get("member_ids", [])
                assert isinstance(member_ids, list)
                for member_id in member_ids:
                    if isinstance(member_id, str):
                        visit(member_id)

        member_ids = scene.get("member_ids", [])
        assert isinstance(member_ids, list)
        for member_id in member_ids:
            if isinstance(member_id, str):
                visit(member_id)
        visible_by_scene.append(visible)

    return visible_by_scene


def _collect_reference_ids(value: object, parent_key: str = "") -> list[str]:
    if isinstance(value, str):
        return [value] if parent_key.endswith(("_ref", "_id")) else []
    if isinstance(value, list):
        return [
            ref
            for item in value
            for ref in _collect_reference_ids(item, parent_key)
        ]
    if not isinstance(value, dict):
        return []

    refs: list[str] = []
    for key, item in value.items():
        if key.endswith(("_refs", "_ids")):
            if isinstance(item, list):
                refs.extend(entry for entry in item if isinstance(entry, str))
            continue
        refs.extend(_collect_reference_ids(item, key))
    return refs


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
def test_open_choice_references_are_renderable(path: Path) -> None:
    payload = _load_fixture(path)
    fragments = payload["fragments"]
    assert isinstance(fragments, list)

    scenes = _renderable_ids_by_scene(fragments)
    assert scenes, f"{path.name} must expose at least one scene"

    for fragment in fragments:
        if not isinstance(fragment, dict) or fragment.get("fragment_type") != "choice":
            continue
        if fragment.get("available") is False:
            continue

        refs = _collect_reference_ids(fragment.get("accepts", {}).get("constraints"))
        if not refs:
            continue

        choice_uid = _fragment_uid(fragment)
        scene = next((ids for ids in scenes if choice_uid in ids), None)
        assert scene is not None, f"{path.name}: choice {choice_uid} is not in a scene"
        for ref in refs:
            assert ref in scene, f"{path.name}: choice {choice_uid} references hidden {ref}"


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
