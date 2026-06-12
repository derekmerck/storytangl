"""Time-parity checks for StoryTangl conformance fixtures.

The harness verifies the JSON-visible part of the contract: pending media and
ritualized outcomes must have an immediate readable fallback, and advisory
timing hints must not require the player to wait for presentation time.
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

TIME_BOUND_MEDIA_ROLES = {"bgm", "sfx", "video"}
BLOCKING_HINT_KEYS = {
    "blocking",
    "require_completion",
    "requires_completion",
    "wait_for_completion",
}


@dataclass(frozen=True)
class TimeParityIssue:
    """A timed fragment lacks an immediate readable fallback."""

    fragment_uid: str
    reason: str
    step_index: int | None = None

    def describe(self) -> str:
        prefix = f"step {self.step_index}: " if self.step_index is not None else ""
        return f"{prefix}fragment {self.fragment_uid}: {self.reason}"


@dataclass(frozen=True)
class EnvelopeTimeParityResult:
    """Registry snapshot plus issues after checking one envelope."""

    registry: FragmentRegistry
    issues: tuple[TimeParityIssue, ...]


def check_runtime_envelope(
    envelope: JsonObject,
    registry: FragmentRegistry | None = None,
    *,
    step_index: int | None = None,
) -> EnvelopeTimeParityResult:
    """Apply one envelope and return time-parity issues."""

    next_registry = apply_runtime_envelope(registry or {}, envelope)
    renderable_uids = current_shell_ids(next_registry)
    issues: list[TimeParityIssue] = []

    for uid in sorted(renderable_uids):
        fragment = next_registry.get(uid)
        if fragment is None:
            continue
        fragment_type = _text(fragment, "fragment_type")
        if fragment_type == "media":
            issues.extend(_check_media(fragment, uid, step_index))
        elif fragment_type == "roll":
            issues.extend(_check_roll(fragment, uid, step_index))

    return EnvelopeTimeParityResult(registry=next_registry, issues=tuple(issues))


def check_sequence(sequence: JsonObject) -> tuple[TimeParityIssue, ...]:
    """Check every envelope in a multi-envelope fixture sequence."""

    registry: FragmentRegistry = {}
    issues: list[TimeParityIssue] = []
    for step_index, envelope in enumerate(_object_list(sequence.get("envelopes")), start=1):
        result = check_runtime_envelope(envelope, registry, step_index=step_index)
        registry = result.registry
        issues.extend(result.issues)
    return tuple(issues)


def assert_no_issues(issues: Sequence[TimeParityIssue]) -> None:
    """Raise an AssertionError with readable issue descriptions."""

    if issues:
        details = "\n".join(issue.describe() for issue in issues)
        raise AssertionError(f"Time-parity violations:\n{details}")


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


def _check_media(
    fragment: JsonObject,
    uid: str,
    step_index: int | None,
) -> list[TimeParityIssue]:
    content_format = _text(fragment, "content_format")
    content = fragment.get("content")
    media_role = _text(fragment, "media_role")
    issues: list[TimeParityIssue] = []

    if not content_format:
        issues.append(TimeParityIssue(uid, "media is missing content_format", step_index))
    if not _has_readable_value(content):
        issues.append(TimeParityIssue(uid, "media is missing readable content", step_index))

    if content_format == "rit":
        status = _text(fragment, "generation_status")
        if status == "ready":
            issues.append(TimeParityIssue(uid, "ready media must resolve beyond rit", step_index))
        elif status not in {None, "pending", "loading", "error"}:
            issues.append(
                TimeParityIssue(uid, f"unknown rit generation_status {status!r}", step_index)
            )

    if media_role in TIME_BOUND_MEDIA_ROLES:
        issues.extend(_blocking_hint_issues(fragment, uid, step_index))
    return issues


def _check_roll(
    fragment: JsonObject,
    uid: str,
    step_index: int | None,
) -> list[TimeParityIssue]:
    issues: list[TimeParityIssue] = []
    if not _text(fragment, "label"):
        issues.append(TimeParityIssue(uid, "roll is missing label", step_index))
    if not _text(fragment, "outcome"):
        issues.append(TimeParityIssue(uid, "roll is missing outcome", step_index))
    if not _object(fragment.get("inputs")) and not _text(fragment, "narrative"):
        issues.append(
            TimeParityIssue(uid, "roll needs inputs or narrative for fallback", step_index)
        )

    ritual_hints = _object(fragment.get("ritual_hints"))
    if ritual_hints is None:
        return issues

    duration = ritual_hints.get("duration_ms")
    if duration is not None and (not _is_int(duration) or duration < 0):
        issues.append(
            TimeParityIssue(uid, "ritual duration_ms must be a non-negative integer", step_index)
        )
    skip_label = ritual_hints.get("skip_label")
    if skip_label is not None and not _has_readable_value(skip_label):
        issues.append(
            TimeParityIssue(uid, "ritual skip_label must be readable when present", step_index)
        )
    issues.extend(_blocking_hint_issues(ritual_hints, uid, step_index))
    return issues


def _blocking_hint_issues(
    mapping: JsonObject,
    uid: str,
    step_index: int | None,
) -> list[TimeParityIssue]:
    issues: list[TimeParityIssue] = []
    for key in sorted(BLOCKING_HINT_KEYS):
        if mapping.get(key) is True:
            issues.append(TimeParityIssue(uid, f"timing hint {key!r} cannot be true", step_index))

    staging_hints = _object(mapping.get("staging_hints"))
    if staging_hints is not None:
        issues.extend(_blocking_hint_issues(staging_hints, uid, step_index))
    return issues


def _has_readable_value(value: JsonValue | None) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_readable_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_readable_value(item) for item in value.values())
    return isinstance(value, (int, float, bool))


def _is_int(value: JsonValue | None) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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
