"""Input-parity checks for StoryTangl conformance fixtures.

The harness verifies that available choices declare enough JSON shape for a
lowest-capability client to build a boring submit control. It does not care
whether a renderer uses buttons, listboxes, text input, or drag/drop flourishes.
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

SUPPORTED_ACCEPTS_KINDS = {
    "pick",
    "text",
    "quantity",
    "raw_command",
    "pieces",
    "place",
    "compose",
}


@dataclass(frozen=True)
class InputParityIssue:
    """A choice cannot be submitted by a lowest-capability client."""

    choice_uid: str
    accepts_path: str
    reason: str
    step_index: int | None = None

    def describe(self) -> str:
        prefix = f"step {self.step_index}: " if self.step_index is not None else ""
        return f"{prefix}choice {self.choice_uid} {self.accepts_path}: {self.reason}"


@dataclass(frozen=True)
class EnvelopeInputParityResult:
    """Registry snapshot plus issues after checking one envelope."""

    registry: FragmentRegistry
    issues: tuple[InputParityIssue, ...]


def check_runtime_envelope(
    envelope: JsonObject,
    registry: FragmentRegistry | None = None,
    *,
    step_index: int | None = None,
) -> EnvelopeInputParityResult:
    """Apply one envelope and return input-parity issues."""

    next_registry = apply_runtime_envelope(registry or {}, envelope)
    renderable_uids = current_shell_ids(next_registry)
    renderable_refs = current_shell_reference_ids(next_registry, renderable_uids)
    issues: list[InputParityIssue] = []

    for choice in _available_choices(next_registry):
        choice_uid = _text(choice, "uid") or "<unknown>"
        if choice_uid not in renderable_uids:
            continue
        accepts = _object(choice.get("accepts"))
        if accepts is None:
            continue
        issues.extend(
            _check_accepts(
                accepts,
                next_registry,
                renderable_refs,
                choice_uid=choice_uid,
                accepts_path="accepts",
                step_index=step_index,
            )
        )

    return EnvelopeInputParityResult(registry=next_registry, issues=tuple(issues))


def check_sequence(sequence: JsonObject) -> tuple[InputParityIssue, ...]:
    """Check every envelope in a multi-envelope fixture sequence."""

    registry: FragmentRegistry = {}
    issues: list[InputParityIssue] = []
    for step_index, envelope in enumerate(_object_list(sequence.get("envelopes")), start=1):
        result = check_runtime_envelope(envelope, registry, step_index=step_index)
        registry = result.registry
        issues.extend(result.issues)
    return tuple(issues)


def assert_no_issues(issues: Sequence[InputParityIssue]) -> None:
    """Raise an AssertionError with readable issue descriptions."""

    if issues:
        details = "\n".join(issue.describe() for issue in issues)
        raise AssertionError(f"Input-parity violations:\n{details}")


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


def _check_accepts(
    accepts: JsonObject,
    registry: FragmentRegistry,
    renderable_refs: set[str],
    *,
    choice_uid: str,
    accepts_path: str,
    step_index: int | None,
) -> list[InputParityIssue]:
    kind = _text(accepts, "kind")
    if kind not in SUPPORTED_ACCEPTS_KINDS:
        return [
            InputParityIssue(
                choice_uid,
                accepts_path,
                "missing or unsupported accepts kind",
                step_index,
            )
        ]

    if kind in {"pick", "text", "raw_command"}:
        return []
    if kind == "quantity":
        return _check_quantity(accepts, choice_uid, accepts_path, step_index)
    if kind == "pieces":
        return _check_pieces(
            accepts,
            registry,
            renderable_refs,
            choice_uid,
            accepts_path,
            step_index,
        )
    if kind == "place":
        return _check_place(
            accepts,
            registry,
            renderable_refs,
            choice_uid,
            accepts_path,
            step_index,
        )
    return _check_compose(accepts, registry, renderable_refs, choice_uid, accepts_path, step_index)


def _check_quantity(
    accepts: JsonObject,
    choice_uid: str,
    accepts_path: str,
    step_index: int | None,
) -> list[InputParityIssue]:
    issues: list[InputParityIssue] = []
    minimum = accepts.get("min")
    maximum = accepts.get("max")
    if minimum is not None and not _is_int(minimum):
        issues.append(
            InputParityIssue(choice_uid, accepts_path, "`min` must be an integer", step_index)
        )
    if maximum is not None and not _is_int(maximum):
        issues.append(
            InputParityIssue(choice_uid, accepts_path, "`max` must be an integer", step_index)
        )
    if _is_int(minimum) and _is_int(maximum) and minimum > maximum:
        issues.append(InputParityIssue(choice_uid, accepts_path, "`min` exceeds `max`", step_index))
    return issues


def _check_pieces(
    accepts: JsonObject,
    registry: FragmentRegistry,
    renderable_refs: set[str],
    choice_uid: str,
    accepts_path: str,
    step_index: int | None,
) -> list[InputParityIssue]:
    issues = _check_selection_bounds(accepts, choice_uid, accepts_path, step_index)
    constraints = _object(accepts.get("constraints"))
    zone_ref = _text(accepts, "target_zone_ref") or _text(constraints, "target_zone_ref")
    if zone_ref is None:
        issues.append(
            InputParityIssue(choice_uid, accepts_path, "missing target_zone_ref", step_index)
        )
        return issues
    if zone_ref not in renderable_refs:
        issues.append(
            InputParityIssue(
                choice_uid,
                accepts_path,
                f"target zone {zone_ref!r} is not renderable",
                step_index,
            )
        )
        return issues
    if _minimum_selection(accepts) > 0 and not _piece_options_in_zone(
        registry,
        zone_ref,
        renderable_refs,
    ):
        issues.append(
            InputParityIssue(
                choice_uid,
                accepts_path,
                f"target zone {zone_ref!r} has no selectable pieces",
                step_index,
            )
        )
    return issues


def _check_place(
    accepts: JsonObject,
    registry: FragmentRegistry,
    renderable_refs: set[str],
    choice_uid: str,
    accepts_path: str,
    step_index: int | None,
) -> list[InputParityIssue]:
    constraints = _object(accepts.get("constraints"))
    source_ref = _text(accepts, "source_zone_ref") or _text(constraints, "source_zone_ref")
    target_ref = _text(accepts, "target_zone_ref") or _text(constraints, "target_zone_ref")
    edge_ref = _text(accepts, "edge_ref") or _text(constraints, "edge_ref")
    issues: list[InputParityIssue] = []

    if source_ref is None:
        issues.append(
            InputParityIssue(choice_uid, accepts_path, "missing source_zone_ref", step_index)
        )
    elif source_ref not in renderable_refs:
        issues.append(
            InputParityIssue(
                choice_uid,
                accepts_path,
                f"source zone {source_ref!r} is not renderable",
                step_index,
            )
        )
    elif not _piece_options_in_zone(registry, source_ref, renderable_refs):
        issues.append(
            InputParityIssue(
                choice_uid,
                accepts_path,
                f"source zone {source_ref!r} has no selectable pieces",
                step_index,
            )
        )

    if target_ref is None and edge_ref is None:
        issues.append(
            InputParityIssue(
                choice_uid,
                accepts_path,
                "missing target_zone_ref or edge_ref",
                step_index,
            )
        )
    elif target_ref is not None and target_ref not in renderable_refs:
        issues.append(
            InputParityIssue(
                choice_uid,
                accepts_path,
                f"target zone {target_ref!r} is not renderable",
                step_index,
            )
        )
    elif edge_ref is not None and edge_ref not in renderable_refs:
        issues.append(
            InputParityIssue(
                choice_uid,
                accepts_path,
                f"edge {edge_ref!r} is not renderable",
                step_index,
            )
        )
    return issues


def _check_compose(
    accepts: JsonObject,
    registry: FragmentRegistry,
    renderable_refs: set[str],
    choice_uid: str,
    accepts_path: str,
    step_index: int | None,
) -> list[InputParityIssue]:
    parts = _object_list(accepts.get("parts"))
    issues: list[InputParityIssue] = []
    if not parts:
        return [
            InputParityIssue(choice_uid, accepts_path, "compose accepts requires parts", step_index)
        ]

    seen_roles: set[str] = set()
    for index, part in enumerate(parts):
        path = f"{accepts_path}.parts[{index}]"
        role = _text(part, "role")
        if role is None:
            issues.append(InputParityIssue(choice_uid, path, "missing role", step_index))
        elif role in seen_roles:
            issues.append(
                InputParityIssue(choice_uid, path, f"duplicate role {role!r}", step_index)
            )
        else:
            seen_roles.add(role)

        child_accepts = _object(part.get("accepts"))
        if child_accepts is None:
            issues.append(InputParityIssue(choice_uid, path, "missing nested accepts", step_index))
            continue
        issues.extend(
            _check_accepts(
                child_accepts,
                registry,
                renderable_refs,
                choice_uid=choice_uid,
                accepts_path=f"{path}.accepts",
                step_index=step_index,
            )
        )
    return issues


def _check_selection_bounds(
    accepts: JsonObject,
    choice_uid: str,
    accepts_path: str,
    step_index: int | None,
) -> list[InputParityIssue]:
    issues: list[InputParityIssue] = []
    minimum = accepts.get("min")
    maximum = accepts.get("max")
    if minimum is not None and not _is_int(minimum):
        issues.append(
            InputParityIssue(choice_uid, accepts_path, "`min` must be an integer", step_index)
        )
    if maximum is not None and not _is_int(maximum):
        issues.append(
            InputParityIssue(choice_uid, accepts_path, "`max` must be an integer", step_index)
        )
    if _is_int(minimum) and _is_int(maximum) and minimum > maximum:
        issues.append(InputParityIssue(choice_uid, accepts_path, "`min` exceeds `max`", step_index))
    return issues


def _minimum_selection(accepts: JsonObject) -> int:
    minimum = accepts.get("min")
    return minimum if _is_int(minimum) else 1


def _piece_options_in_zone(
    registry: FragmentRegistry,
    zone_ref: str,
    renderable_refs: set[str],
) -> list[JsonObject]:
    zone = _fragment_by_uid_or_domain_id(registry, zone_ref)
    if zone is None:
        return []
    pieces: list[JsonObject] = []
    for member_id in _string_list(zone.get("member_ids")):
        if member_id not in renderable_refs:
            continue
        member = _fragment_by_uid_or_domain_id(registry, member_id)
        if (
            member is not None
            and member.get("fragment_type") == "piece"
            and _text(member, "piece_id")
        ):
            pieces.append(member)
    return pieces


def _is_int(value: JsonValue | None) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _fragment_by_uid_or_domain_id(
    registry: FragmentRegistry,
    ref: str,
) -> JsonObject | None:
    fragment = registry.get(ref)
    if fragment is not None:
        return fragment
    for candidate in registry.values():
        if ref in {
            value
            for key in ("piece_id", "state_id", "zone_id")
            if isinstance((value := candidate.get(key)), str)
        }:
            return candidate
    return None


def _available_choices(registry: FragmentRegistry) -> list[JsonObject]:
    return [
        fragment
        for fragment in registry.values()
        if fragment.get("fragment_type") == "choice" and fragment.get("available") is not False
    ]


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
