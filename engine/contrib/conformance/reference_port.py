"""UI-neutral reference port for StoryTangl conformance fixtures.

The module builds a small view model from portable JSON fixtures. Terminal,
Tkinter, and other low-capability clients can render that model in their own
medium without importing engine models or calling the service layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
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


@dataclass(frozen=True)
class ChoiceControl:
    """A client-neutral choice control description."""

    uid: str | None
    edge_id: str | None
    label: str
    available: bool
    hotkey: str
    prompt: str
    accepts_kind: str | None = None
    locked_reason: str | None = None
    accepts: JsonObject | None = None


@dataclass(frozen=True)
class RenderItem:
    """One observable fixture item for a concrete client to display."""

    role: str
    text: str
    indent: int = 0
    ref_id: str | None = None
    choice: ChoiceControl | None = None
    data: JsonObject | None = None

    def as_text(self) -> str:
        return f"{'  ' * self.indent}{self.text}"


@dataclass(frozen=True)
class RenderDocument:
    """A rendered fixture view model."""

    kind: str
    items: tuple[RenderItem, ...]

    @property
    def choices(self) -> tuple[ChoiceControl, ...]:
        return tuple(item.choice for item in self.items if item.choice is not None)


def load_fixture(path: Path) -> JsonObject:
    """Load a fixture JSON object."""

    with path.open(encoding="utf-8") as fixture_file:
        payload = json.load(fixture_file)

    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(JsonObject, payload)


def render_fixture_document(payload: JsonObject) -> RenderDocument:
    """Render a RuntimeEnvelope or ProjectedState fixture to a view model."""

    if isinstance(payload.get("fragments"), list):
        return render_runtime_envelope_document(payload)
    if isinstance(payload.get("sections"), list):
        return render_projected_state_document(payload)
    return RenderDocument("unsupported", (_item("fallback", "Unsupported fixture shape."),))


def render_fixture(payload: JsonObject) -> list[str]:
    """Render a fixture to plain text lines."""

    return format_document(render_fixture_document(payload))


def format_document(document: RenderDocument) -> list[str]:
    """Format a rendered document as terminal-friendly text lines."""

    return [item.as_text() for item in document.items]


def render_runtime_envelope_document(envelope: JsonObject) -> RenderDocument:
    """Render a RuntimeEnvelope-like JSON object to a generic view model."""

    fragments = _object_list(envelope.get("fragments"))
    registry = _registry_after_controls(fragments)
    scenes = [
        fragment
        for fragment in registry.values()
        if fragment.get("fragment_type") == "group" and fragment.get("group_type") == "scene"
    ]

    items = [_item("title", _runtime_title(envelope))]
    visited: set[str] = set()
    if not scenes:
        items.append(_item("empty", "(no scene)"))
    for scene in scenes:
        scene_uid = _text(scene, "uid")
        if scene_uid:
            visited.add(scene_uid)
        member_ids = _string_list(scene.get("member_ids"))
        if not member_ids:
            items.append(_item("empty", "(empty scene)", ref_id=scene_uid))
            continue
        item_count = len(items)
        for member_id in member_ids:
            items.extend(_render_fragment(member_id, registry, envelope, 0, visited))
        if len(items) == item_count:
            items.append(_item("empty", "(empty scene)", ref_id=scene_uid))

    for uid, fragment in registry.items():
        fragment_type = _text(fragment, "fragment_type")
        if uid not in visited and fragment_type != "group":
            items.extend(_render_fragment(uid, registry, envelope, 0, visited))
    return RenderDocument("runtime_envelope", tuple(items))


def render_projected_state_document(state: JsonObject) -> RenderDocument:
    """Render a ProjectedState-like JSON object to a generic view model."""

    items = [_item("title", "Projected State")]
    for section in _object_list(state.get("sections")):
        section_id = _text(section, "section_id")
        title = _text(section, "title", "section_id") or "Untitled"
        items.append(_item("projected_section", f"{title}:", ref_id=section_id))
        value = _object(section.get("value"))
        if value is None:
            items.append(_item("empty", "(empty)", indent=1, ref_id=section_id))
            continue
        section_items = _render_section_value(value, section_id)
        if section_items:
            items.extend(section_items)
        else:
            items.append(_item("empty", "(empty)", indent=1, ref_id=section_id))
    return RenderDocument("projected_state", tuple(items))


def _runtime_title(envelope: JsonObject) -> str:
    bits = ["Runtime Envelope"]
    cursor_id = _text(envelope, "cursor_id")
    step = envelope.get("step")
    if cursor_id:
        bits.append(f"cursor={cursor_id}")
    if isinstance(step, int):
        bits.append(f"step={step}")
    return " | ".join(bits)


def _registry_after_controls(fragments: Sequence[JsonObject]) -> FragmentRegistry:
    registry: FragmentRegistry = {}
    for fragment in fragments:
        fragment_type = _text(fragment, "fragment_type")
        if fragment_type == "delete":
            ref_id = _text(fragment, "ref_id", "reference_id")
            if ref_id:
                registry.pop(ref_id, None)
            continue
        if fragment_type == "update":
            ref_id = _text(fragment, "ref_id", "reference_id")
            payload = _object(fragment.get("payload"))
            if ref_id and payload is not None:
                existing = registry.get(ref_id, {"uid": ref_id})
                registry[ref_id] = {**existing, **payload, "uid": ref_id}
            continue
        uid = _text(fragment, "uid")
        if uid:
            registry[uid] = fragment
    return registry


def _render_fragment(
    uid: str,
    registry: FragmentRegistry,
    envelope: JsonObject,
    indent: int,
    visited: set[str],
) -> list[RenderItem]:
    fragment = registry.get(uid)
    if fragment is None or uid in visited:
        return []
    visited.add(uid)

    fragment_type = _text(fragment, "fragment_type") or "unknown"
    if fragment_type == "content":
        text = _text(fragment, "content", "text", "label") or ""
        return [_item("content", text, indent=indent, ref_id=uid)]
    if fragment_type == "group":
        return _render_group(fragment, registry, envelope, indent, visited)
    if fragment_type == "attributed":
        return [_render_attributed(fragment, indent)]
    if fragment_type == "media":
        return [_item("media", _render_media(fragment), indent=indent, ref_id=uid)]
    if fragment_type == "kv":
        return _render_kv(fragment, indent)
    if fragment_type == "choice":
        return [_render_choice(fragment, registry, envelope, indent)]
    if fragment_type == "piece":
        return [
            _item(
                "piece",
                _render_piece(fragment),
                indent=indent,
                ref_id=uid,
                data=_piece_data(fragment),
            )
        ]
    if fragment_type == "interpretation":
        text = _render_interpretation(fragment)
        return [_item("interpretation", text, indent=indent, ref_id=uid)]
    if fragment_type == "user_event":
        return [_item("user_event", _render_user_event(fragment), indent=indent, ref_id=uid)]

    label = _text(fragment, "label", "content", "text") or fragment_type
    return [_item("fallback", f"[unsupported {fragment_type}] {label}", indent, uid)]


def _render_group(
    fragment: JsonObject,
    registry: FragmentRegistry,
    envelope: JsonObject,
    indent: int,
    visited: set[str],
) -> list[RenderItem]:
    group_type = _text(fragment, "group_type") or "group"
    member_ids = _string_list(fragment.get("member_ids"))
    uid = _text(fragment, "uid")

    if group_type == "zone":
        label = _fragment_label(fragment, "Zone")
        items = [_item("zone_label", f"{label}:", indent=indent, ref_id=uid)]
        if not member_ids:
            items.append(_item("empty", "(empty)", indent=indent + 1, ref_id=uid))
        for member_id in member_ids:
            items.extend(_render_fragment(member_id, registry, envelope, indent + 1, visited))
        return items

    if group_type == "dialog":
        items = [_item("dialog_label", "Dialog:", indent=indent, ref_id=uid)]
        for member_id in member_ids:
            items.extend(_render_fragment(member_id, registry, envelope, indent + 1, visited))
        return items

    items = []
    for member_id in member_ids:
        items.extend(_render_fragment(member_id, registry, envelope, indent, visited))
    return items or [_item("empty", "(empty group)", indent=indent, ref_id=uid)]


def _render_attributed(fragment: JsonObject, indent: int) -> RenderItem:
    uid = _text(fragment, "uid")
    who = _text(fragment, "who") or "Unknown"
    content = _text(fragment, "content") or ""
    how = _text(fragment, "how")
    if how:
        return _item("attributed", f"{who} [{how}]: {content}", indent=indent, ref_id=uid)

    hints = _object(fragment.get("hints"))
    if hints is None:
        return _item("attributed", f"{who}: {content}", indent=indent, ref_id=uid)

    tags = [
        value
        for key in ("tone", "visibility", "role")
        if isinstance((value := hints.get(key)), str)
    ]
    suffix = f" [{', '.join(tags)}]" if tags else ""
    return _item("attributed", f"{who}{suffix}: {content}", indent=indent, ref_id=uid)


def _render_media(fragment: JsonObject) -> str:
    uid = _text(fragment, "uid") or "media"
    content_format = _text(fragment, "content_format") or "unknown"
    content = _text(fragment, "content") or ""
    status = _text(fragment, "generation_status")
    if content_format == "rit":
        status_text = f" {status}" if status else ""
        return f"[media:{uid}{status_text} {content}]"
    return f"[media:{uid} {content_format} {content}]"


def _render_kv(fragment: JsonObject, indent: int) -> list[RenderItem]:
    uid = _text(fragment, "uid")
    rows = _list(fragment.get("content"))
    items: list[RenderItem] = []
    for row in rows:
        if isinstance(row, list) and len(row) >= 2:
            label = row[0]
            value = row[1]
            items.append(_item("fact", f"{label}: {value}", indent=indent, ref_id=uid))
        elif isinstance(row, dict):
            label = row.get("key") or row.get("label")
            value = row.get("value")
            if label is not None:
                items.append(_item("fact", f"{label}: {value}", indent=indent, ref_id=uid))
    return items or [_item("empty", "(empty facts)", indent=indent, ref_id=uid)]


def _render_choice(
    fragment: JsonObject,
    registry: FragmentRegistry,
    envelope: JsonObject,
    indent: int,
) -> RenderItem:
    uid = _text(fragment, "uid")
    label = _text(fragment, "text", "label", "content") or uid or "Choice"
    available = fragment.get("available") is not False
    hotkey = _choice_hotkey(fragment) if available else "x"
    accepts = _object(fragment.get("accepts"))
    accepts_kind = _text(accepts, "kind") if accepts is not None else None
    prompt = _accepts_prompt(accepts, registry, envelope)
    locked_reason = None if available else _text(fragment, "locked_reason", "unavailable_reason")

    choice = ChoiceControl(
        uid=uid,
        edge_id=_text(fragment, "edge_id"),
        label=label,
        available=available,
        hotkey=hotkey,
        prompt=prompt,
        accepts_kind=accepts_kind,
        locked_reason=locked_reason,
        accepts=accepts,
    )
    return _item("choice", _choice_text(choice), indent=indent, ref_id=uid, choice=choice)


def _choice_text(choice: ChoiceControl) -> str:
    if not choice.available:
        suffix = f" [locked: {choice.locked_reason}]" if choice.locked_reason else " [locked]"
        return f"x) {choice.label}{suffix}"
    return f"{choice.hotkey}) {choice.label}{choice.prompt}"


def _choice_hotkey(fragment: JsonObject) -> str:
    hints = _object(fragment.get("ui_hints"))
    hotkey = _text(hints, "hotkey") if hints is not None else None
    return hotkey or "*"


def _accepts_prompt(
    accepts: JsonObject | None,
    registry: FragmentRegistry,
    envelope: JsonObject,
) -> str:
    if accepts is None:
        return ""

    kind = _text(accepts, "kind")
    if not kind or kind == "pick":
        return ""

    if kind == "raw_command":
        examples = _grammar_examples(envelope)
        if examples:
            return f" <command: e.g. {examples[0]}>"
        return " <command>"

    if kind == "text":
        placeholder = _text(accepts, "placeholder")
        return f" <text: {placeholder}>" if placeholder else " <text>"

    if kind == "quantity":
        minimum = accepts.get("min")
        maximum = accepts.get("max")
        unit = _text(accepts, "unit")
        bounds = _quantity_bounds(minimum, maximum)
        unit_text = f" {unit}" if unit else ""
        return f" <quantity {bounds}{unit_text}>"

    if kind == "pieces":
        minimum = accepts.get("min")
        maximum = accepts.get("max")
        constraints = _object(accepts.get("constraints"))
        zone_ref = _text(constraints, "target_zone_ref") if constraints is not None else None
        zone = registry.get(zone_ref) if zone_ref else None
        zone_label = _fragment_label(zone, zone_ref or "zone") if zone is not None else "zone"
        count = _selection_count(minimum, maximum, "piece")
        return f" <select {count} from {zone_label}>"

    return f" <{kind}>"


def _render_piece(fragment: JsonObject) -> str:
    label = _fragment_label(fragment, "piece")
    state = _text(fragment, "display_state")
    return f"- {label} [{state}]" if state else f"- {label}"


def _piece_data(fragment: JsonObject) -> JsonObject:
    data: JsonObject = {}
    piece_id = _text(fragment, "piece_id")
    zone_ref = _text(fragment, "zone_ref")
    label = _fragment_label(fragment, "piece")
    if piece_id:
        data["piece_id"] = piece_id
    if zone_ref:
        data["zone_ref"] = zone_ref
    if label:
        data["label"] = label
    return data


def _render_interpretation(fragment: JsonObject) -> str:
    outcome = _text(fragment, "outcome") or "interpretation"
    content = _text(fragment, "content") or ""
    command_text = _text(fragment, "command_text")
    prefix = f"[interpretation:{outcome}]"
    if command_text:
        prefix = f'{prefix} "{command_text}"'
    return f"{prefix} {content}"


def _render_user_event(fragment: JsonObject) -> str:
    event_type = _text(fragment, "event_type") or "user_event"
    content = fragment.get("content")
    return f"[event:{event_type}] {json.dumps(content, sort_keys=True)}"


def _render_section_value(value: JsonObject, ref_id: str | None) -> list[RenderItem]:
    value_type = _text(value, "value_type")
    if value_type == "scalar":
        scalar = value.get("value")
        if scalar is None:
            return []
        return [_item("projected_value", str(scalar), indent=1, ref_id=ref_id)]

    if value_type == "kv_list":
        return [
            _item("projected_value", f"{item.get('key')}: {item.get('value')}", 1, ref_id)
            for item in _object_list(value.get("items"))
            if item.get("key") is not None
        ]

    if value_type == "item_list":
        return [
            _item("projected_value", _render_projected_item(item), 1, ref_id)
            for item in _object_list(value.get("items"))
        ]

    if value_type == "table":
        columns = [str(column) for column in _list(value.get("columns"))]
        rows = _list(value.get("rows"))
        items = [_item("projected_value", " | ".join(columns), 1, ref_id)] if columns else []
        for row in rows:
            if isinstance(row, list):
                items.append(_item("projected_value", " | ".join(str(cell) for cell in row), 1))
        return items

    if value_type == "badges":
        badges = _list(value.get("items"))
        if not badges:
            return []
        return [_item("projected_value", ", ".join(str(item) for item in badges), 1, ref_id)]

    return [_item("fallback", f"[unsupported {value_type or 'value'}]", indent=1, ref_id=ref_id)]


def _render_projected_item(item: JsonObject) -> str:
    label = _text(item, "label") or "(item)"
    detail = _text(item, "detail")
    tags = [str(tag) for tag in _list(item.get("tags"))]
    extras = [value for value in (detail, ", ".join(tags) if tags else None) if value]
    return f"{label}: {' | '.join(extras)}" if extras else label


def _fragment_label(fragment: JsonObject | None, fallback: str) -> str:
    if fragment is None:
        return fallback
    hints = _object(fragment.get("hints"))
    return (
        (_text(hints, "label_text") if hints is not None else None)
        or _text(fragment, "label", "content", "text", "piece_id")
        or fallback
    )


def _grammar_examples(envelope: JsonObject) -> list[str]:
    metadata = _object(envelope.get("metadata"))
    grammar = _object(metadata.get("grammar")) if metadata is not None else None
    return [item for item in _string_list(grammar.get("examples") if grammar else None)]


def _quantity_bounds(minimum: JsonValue, maximum: JsonValue) -> str:
    if isinstance(minimum, int) and isinstance(maximum, int):
        return f"{minimum}-{maximum}"
    if isinstance(minimum, int):
        return f">= {minimum}"
    if isinstance(maximum, int):
        return f"<= {maximum}"
    return "value"


def _selection_count(minimum: JsonValue, maximum: JsonValue, unit: str) -> str:
    if isinstance(minimum, int) and isinstance(maximum, int) and minimum == maximum:
        noun = unit if minimum == 1 else f"{unit}s"
        return f"{minimum} {noun}"
    if isinstance(minimum, int) and isinstance(maximum, int):
        return f"{minimum}-{maximum} {unit}s"
    return f"{unit}s"


def _item(
    role: str,
    text: str,
    indent: int = 0,
    ref_id: str | None = None,
    choice: ChoiceControl | None = None,
    data: JsonObject | None = None,
) -> RenderItem:
    return RenderItem(
        role=role,
        text=text,
        indent=indent,
        ref_id=ref_id,
        choice=choice,
        data=data,
    )


def _text(record: JsonObject | None, *keys: str) -> str | None:
    if record is None:
        return None
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _object(value: JsonValue | object) -> JsonObject | None:
    return cast(JsonObject, value) if isinstance(value, dict) else None


def _list(value: JsonValue | object) -> list[JsonValue]:
    return cast(list[JsonValue], value) if isinstance(value, list) else []


def _object_list(value: JsonValue | object) -> list[JsonObject]:
    return [cast(JsonObject, item) for item in _list(value) if isinstance(item, dict)]


def _string_list(value: JsonValue | object) -> list[str]:
    return [item for item in _list(value) if isinstance(item, str)]
