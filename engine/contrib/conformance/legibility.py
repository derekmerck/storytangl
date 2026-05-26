"""Decision-legibility checks for StoryTangl conformance fixtures.

The harness is intentionally JSON-only. It validates the portable rule that an
available choice may only reference state that the current shell can render.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, cast


JsonValue = (
    str
    | int
    | float
    | bool
    | None
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)
JsonObject = dict[str, JsonValue]
FragmentRegistry = dict[str, JsonObject]

REFERENCE_KEYS = {
    "blocker_ref",
    "blocker_refs",
    "fragment_ref",
    "fragment_refs",
    "piece_id",
    "piece_ids",
    "piece_ref",
    "piece_refs",
    "source_zone_ref",
    "state_ref",
    "state_refs",
    "target_zone_ref",
    "token_ref",
    "token_refs",
    "zone_id",
    "zone_ids",
    "zone_ref",
    "zone_refs",
}
CHOICE_REFERENCE_SURFACES = (
    "accepts",
    "blockers",
    "cost_previews",
    "ui_hints",
)

@dataclass(frozen=True)
class LegibilityIssue:
    """A choice references state that is not renderable in the current shell."""

    choice_uid: str
    ref_id: str
    reason: str
    step_index: int | None = None

    def describe(self) -> str:
        prefix = f"step {self.step_index}: " if self.step_index is not None else ""
        return f"{prefix}choice {self.choice_uid} references {self.ref_id}: {self.reason}"


@dataclass(frozen=True)
class EnvelopeLegibilityResult:
    """Registry snapshot plus issues after checking one envelope."""

    registry: FragmentRegistry
    issues: tuple[LegibilityIssue, ...]


def check_runtime_envelope(
    envelope: JsonObject,
    registry: FragmentRegistry | None = None,
    *,
    step_index: int | None = None,
) -> EnvelopeLegibilityResult:
    """Apply one envelope and return decision-legibility issues."""

    next_registry = apply_runtime_envelope(registry or {}, envelope)
    renderable_uids = current_shell_ids(next_registry)
    renderable_refs = current_shell_reference_ids(next_registry, renderable_uids)
    issues: list[LegibilityIssue] = []

    for choice in _available_choices(next_registry):
        choice_uid = _text(choice, "uid") or "<unknown>"
        if choice_uid not in renderable_uids:
            issues.append(
                LegibilityIssue(
                    choice_uid=choice_uid,
                    ref_id=choice_uid,
                    reason="choice is not renderable",
                    step_index=step_index,
                )
            )
            continue

        for ref_id in sorted(choice_reference_ids(choice)):
            if ref_id not in renderable_refs:
                issues.append(
                    LegibilityIssue(
                        choice_uid=choice_uid,
                        ref_id=ref_id,
                        reason="referenced state is not renderable",
                        step_index=step_index,
                    )
                )

    return EnvelopeLegibilityResult(registry=next_registry, issues=tuple(issues))


def check_sequence(sequence: JsonObject) -> tuple[LegibilityIssue, ...]:
    """Check every envelope in a multi-envelope fixture sequence."""

    registry: FragmentRegistry = {}
    issues: list[LegibilityIssue] = []
    for step_index, envelope in enumerate(_object_list(sequence.get("envelopes")), start=1):
        result = check_runtime_envelope(envelope, registry, step_index=step_index)
        registry = result.registry
        issues.extend(result.issues)
    return tuple(issues)


def assert_no_issues(issues: Sequence[LegibilityIssue]) -> None:
    """Raise an AssertionError with readable issue descriptions."""

    if issues:
        details = "\n".join(issue.describe() for issue in issues)
        raise AssertionError(f"Decision-legibility violations:\n{details}")


def apply_runtime_envelope(registry: FragmentRegistry, envelope: JsonObject) -> FragmentRegistry:
    """Return the fragment registry after applying update/delete controls."""

    next_registry = dict(registry)
    for fragment in _object_list(envelope.get("fragments")):
        fragment_type = _text(fragment, "fragment_type")
        if fragment_type == "delete":
            ref_id = _text(fragment, "ref_id", "reference_id")
            if ref_id:
                next_registry.pop(ref_id, None)
            continue
        if fragment_type == "update":
            ref_id = _text(fragment, "ref_id", "reference_id")
            payload = _object(fragment.get("payload"))
            if ref_id and payload is not None:
                existing = next_registry.get(ref_id, {"uid": ref_id})
                next_registry[ref_id] = {**existing, **payload, "uid": ref_id}
            continue
        uid = _text(fragment, "uid")
        if uid:
            next_registry[uid] = fragment
    return next_registry


def current_shell_ids(registry: FragmentRegistry) -> set[str]:
    """Return fragment ids reachable from every rendered scene group."""

    renderable: set[str] = set()
    scenes = [
        fragment
        for fragment in registry.values()
        if fragment.get("fragment_type") == "group" and fragment.get("group_type") == "scene"
    ]

    def visit(uid: str) -> None:
        if uid in renderable:
            return
        fragment = registry.get(uid)
        if fragment is None:
            return
        renderable.add(uid)
        if fragment.get("fragment_type") != "group":
            return
        for member_id in _string_list(fragment.get("member_ids")):
            visit(member_id)

    for scene in scenes:
        scene_uid = _text(scene, "uid")
        if scene_uid:
            visit(scene_uid)
    return renderable


def current_shell_reference_ids(
    registry: FragmentRegistry,
    renderable_uids: set[str],
) -> set[str]:
    """Return uid plus stable domain ids for renderable fragments."""

    refs = set(renderable_uids)
    for uid in renderable_uids:
        fragment = registry.get(uid)
        if fragment is None:
            continue
        refs.update(
            value
            for key in ("piece_id", "state_id", "zone_id")
            if isinstance((value := fragment.get(key)), str)
        )
    return refs


def choice_reference_ids(choice: JsonObject) -> set[str]:
    """Collect renderable-state references from a choice's decision surfaces."""

    refs: set[str] = set()
    for key in CHOICE_REFERENCE_SURFACES:
        refs.update(_collect_reference_ids(choice.get(key)))
    return refs


def _available_choices(registry: FragmentRegistry) -> list[JsonObject]:
    return [
        fragment
        for fragment in registry.values()
        if fragment.get("fragment_type") == "choice" and fragment.get("available") is not False
    ]


def _collect_reference_ids(value: JsonValue | None, parent_key: str = "") -> set[str]:
    if isinstance(value, str):
        return {value} if parent_key in REFERENCE_KEYS else set()
    if isinstance(value, list):
        if parent_key in REFERENCE_KEYS:
            return {item for item in value if isinstance(item, str)}
        return {ref_id for item in value for ref_id in _collect_reference_ids(item, parent_key)}
    if not isinstance(value, dict):
        return set()

    refs: set[str] = set()
    for key, item in value.items():
        refs.update(_collect_reference_ids(item, key))
    return refs


def _object(value: JsonValue | None) -> JsonObject | None:
    return cast(JsonObject, value) if isinstance(value, dict) else None


def _object_list(value: JsonValue | None) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [cast(JsonObject, item) for item in value if isinstance(item, dict)]


def _string_list(value: JsonValue | None) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _text(mapping: JsonObject | None, *keys: str) -> str | None:
    if mapping is None:
        return None
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            return value
    return None
