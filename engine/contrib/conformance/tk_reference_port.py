#!/usr/bin/env python3
"""Tiny Tkinter reference port for StoryTangl conformance fixtures.

This adapter consumes the UI-neutral ``reference_port`` view model. It treats
fixture JSON as the transport output and prints collected submissions instead
of calling a backend.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Mapping, Sequence, cast


def _load_reference_port() -> ModuleType:
    module_path = Path(__file__).with_name("reference_port.py")
    spec = importlib.util.spec_from_file_location("reference_port", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_REFERENCE_PORT = _load_reference_port()

JsonValue = _REFERENCE_PORT.JsonValue
JsonObject = _REFERENCE_PORT.JsonObject
ChoiceControl = _REFERENCE_PORT.ChoiceControl
RenderDocument = _REFERENCE_PORT.RenderDocument
RenderItem = _REFERENCE_PORT.RenderItem

load_fixture = _REFERENCE_PORT.load_fixture
render_fixture_document = _REFERENCE_PORT.render_fixture_document


@dataclass(frozen=True)
class PieceOption:
    """A visible piece option exposed by a referenced zone."""

    value: str
    label: str
    ref_id: str | None
    zone_ref: str


@dataclass(frozen=True)
class InputControlPlan:
    """Tk-friendly description of the input attached to a choice."""

    kind: str
    widget: str
    payload_key: str | None = None
    minimum: int | None = None
    maximum: int | None = None
    step: int | None = None
    unit: str | None = None
    source_zone_ref: str | None = None
    target_zone_ref: str | None = None
    options: tuple[PieceOption, ...] = ()


@dataclass(frozen=True)
class WidgetPlan:
    """A planned Tk widget without importing Tkinter."""

    role: str
    widget: str
    text: str
    indent: int = 0
    ref_id: str | None = None
    enabled: bool = True
    choice: ChoiceControl | None = None
    input: InputControlPlan | None = None


@dataclass(frozen=True)
class Submission:
    """Payload a Tk action would send to the backend."""

    edge_id: str | None
    choice_uid: str | None
    payload: JsonObject

    def as_transport(self) -> JsonObject:
        return {
            "edge_id": self.edge_id,
            "choice_uid": self.choice_uid,
            "payload": self.payload,
        }


ROLE_WIDGETS: Mapping[str, str] = {
    "title": "label",
    "content": "text",
    "attributed": "label",
    "dialog_label": "label",
    "media": "media_placeholder",
    "zone_label": "labelframe_label",
    "piece": "piece_label",
    "fact": "label",
    "interpretation": "label",
    "user_event": "label",
    "projected_section": "labelframe_label",
    "projected_value": "label",
    "empty": "label",
    "fallback": "label",
}


def load_fixture_plan(path: Path) -> tuple[RenderDocument, tuple[WidgetPlan, ...]]:
    """Load a conformance fixture and plan its Tk widgets."""

    document = render_fixture_document(load_fixture(path))
    return document, build_widget_plan(document)


def build_widget_plan(document: RenderDocument) -> tuple[WidgetPlan, ...]:
    """Map a neutral render document to Tk-oriented widget plans."""

    pieces_by_zone = _piece_options_by_zone(document)
    plans: list[WidgetPlan] = []
    for item in document.items:
        if item.choice is None:
            plans.append(
                WidgetPlan(
                    role=item.role,
                    widget=ROLE_WIDGETS.get(item.role, "label"),
                    text=item.text,
                    indent=item.indent,
                    ref_id=item.ref_id,
                )
            )
            continue

        input_plan = _choice_input_plan(item.choice, pieces_by_zone)
        widget = input_plan.widget if input_plan is not None else "button"
        plans.append(
            WidgetPlan(
                role="choice",
                widget=widget,
                text=item.choice.label,
                indent=item.indent,
                ref_id=item.ref_id,
                enabled=item.choice.available,
                choice=item.choice,
                input=input_plan,
            )
        )
    return tuple(plans)


def collect_submission(plan: WidgetPlan, value: JsonValue = None) -> Submission:
    """Build the transport payload for a planned choice submission."""

    if plan.choice is None:
        raise ValueError("Only choice widget plans can submit")
    if not plan.enabled:
        raise ValueError(f"Choice is locked: {plan.choice.label}")

    input_plan = plan.input
    if input_plan is None or input_plan.kind == "pick":
        payload: JsonObject = {}
    elif input_plan.kind in {"text", "raw_command"}:
        if not isinstance(value, str):
            raise ValueError(f"{input_plan.kind} choices require string input")
        payload = {"text": value}
    elif input_plan.kind == "quantity":
        quantity = _int_value(value)
        if input_plan.minimum is not None and quantity < input_plan.minimum:
            raise ValueError(f"Quantity must be >= {input_plan.minimum}")
        if input_plan.maximum is not None and quantity > input_plan.maximum:
            raise ValueError(f"Quantity must be <= {input_plan.maximum}")
        payload = {"quantity": quantity}
    elif input_plan.kind == "pieces":
        piece_ids = _selected_piece_ids(value)
        _validate_piece_selection(input_plan, piece_ids)
        payload = {"piece_ids": piece_ids}
    elif input_plan.kind == "place":
        piece_ids = _selected_piece_ids(value)
        _validate_piece_selection(input_plan, piece_ids)
        piece_id = piece_ids[0]
        payload = {
            "piece_id": piece_id,
            "source_zone_ref": input_plan.source_zone_ref,
            "target_zone_ref": input_plan.target_zone_ref,
        }
    else:
        payload = {}

    return Submission(
        edge_id=plan.choice.edge_id,
        choice_uid=plan.choice.uid,
        payload=payload,
    )


def inspect_fixture(path: Path) -> JsonObject:
    """Return a JSON-serializable inspection of the Tk adapter plan."""

    document, plans = load_fixture_plan(path)
    return {
        "kind": document.kind,
        "widgets": [_widget_plan_json(plan) for plan in plans],
        "sample_submissions": [
            submission.as_transport()
            for plan in plans
            if plan.choice is not None and plan.enabled
            if (submission := _sample_submission(plan)) is not None
        ],
    }


class TkReferenceApp:
    """Minimal Tkinter renderer for the reference-port view model."""

    def __init__(self, root: object, document: RenderDocument) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.tk = tk
        self.ttk = ttk
        self.plans = build_widget_plan(document)
        self.submissions: list[Submission] = []
        root.title(f"StoryTangl {document.kind}")
        self._build()

    def _build(self) -> None:
        outer = self.ttk.Frame(self.root, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        for row, plan in enumerate(self.plans):
            self._build_plan(outer, row, plan)

    def _build_plan(self, parent: object, row: int, plan: WidgetPlan) -> None:
        if plan.choice is None:
            label = self.ttk.Label(
                parent,
                text=f"{'  ' * plan.indent}{plan.text}",
                wraplength=720,
            )
            label.grid(row=row, column=0, sticky="w", pady=2)
            return

        frame = self.ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=4)
        frame.columnconfigure(1, weight=1)
        if plan.input is None or plan.input.kind == "pick":
            self._button(frame, plan, 0, 0)
        elif plan.input.kind in {"text", "raw_command"}:
            self._entry_choice(frame, plan)
        elif plan.input.kind == "quantity":
            self._quantity_choice(frame, plan)
        elif plan.input.kind in {"pieces", "place"}:
            self._piece_choice(frame, plan)
        else:
            self._button(frame, plan, 0, 0)

    def _button(self, parent: object, plan: WidgetPlan, row: int, column: int) -> None:
        state = "normal" if plan.enabled else "disabled"
        button = self.ttk.Button(
            parent,
            text=plan.text,
            state=state,
            command=lambda plan=plan: self._submit(plan),
        )
        button.grid(row=row, column=column, sticky="w")
        if not plan.enabled and plan.choice and plan.choice.locked_reason:
            reason = self.ttk.Label(parent, text=plan.choice.locked_reason)
            reason.grid(row=row, column=column + 1, sticky="w", padx=(8, 0))

    def _entry_choice(self, parent: object, plan: WidgetPlan) -> None:
        input_plan = cast(InputControlPlan, plan.input)
        variable = self.tk.StringVar()
        label = self.ttk.Label(parent, text=plan.text)
        label.grid(row=0, column=0, sticky="w")
        entry = self.ttk.Entry(parent, textvariable=variable, state=_tk_state(plan))
        entry.grid(row=0, column=1, sticky="ew", padx=6)
        button = self.ttk.Button(
            parent,
            text="Submit",
            state=_tk_state(plan),
            command=lambda plan=plan, variable=variable: self._submit(plan, variable.get()),
        )
        button.grid(row=0, column=2, sticky="w")
        if input_plan.kind == "raw_command" and plan.choice and plan.choice.prompt:
            hint = self.ttk.Label(parent, text=plan.choice.prompt.strip())
            hint.grid(row=1, column=1, sticky="w", padx=6)

    def _quantity_choice(self, parent: object, plan: WidgetPlan) -> None:
        input_plan = cast(InputControlPlan, plan.input)
        variable = self.tk.StringVar(value=str(input_plan.minimum or 0))
        label = self.ttk.Label(parent, text=plan.text)
        label.grid(row=0, column=0, sticky="w")
        if input_plan.minimum is not None and input_plan.maximum is not None:
            field = self.ttk.Spinbox(
                parent,
                from_=input_plan.minimum,
                to=input_plan.maximum,
                increment=input_plan.step or 1,
                textvariable=variable,
                state=_tk_state(plan),
                width=8,
            )
        else:
            field = self.ttk.Entry(parent, textvariable=variable, state=_tk_state(plan), width=8)
        field.grid(row=0, column=1, sticky="w", padx=6)
        bounds = _quantity_bounds_text(input_plan)
        self.ttk.Label(parent, text=bounds).grid(row=0, column=2, sticky="w")
        button = self.ttk.Button(
            parent,
            text="Submit",
            state=_tk_state(plan),
            command=lambda plan=plan, variable=variable: self._submit(plan, variable.get()),
        )
        button.grid(row=0, column=3, sticky="w", padx=(8, 0))

    def _piece_choice(self, parent: object, plan: WidgetPlan) -> None:
        input_plan = cast(InputControlPlan, plan.input)
        self.ttk.Label(parent, text=plan.text).grid(row=0, column=0, sticky="w")
        variables: dict[str, object] = {}
        for index, option in enumerate(input_plan.options, start=1):
            variable = self.tk.BooleanVar(value=False)
            variables[option.value] = variable
            check = self.ttk.Checkbutton(
                parent,
                text=option.label,
                variable=variable,
                state=_tk_state(plan),
            )
            check.grid(row=index, column=1, sticky="w", padx=6)
        button = self.ttk.Button(
            parent,
            text="Submit",
            state=_tk_state(plan),
            command=lambda plan=plan, variables=variables: self._submit(
                plan,
                [value for value, variable in variables.items() if variable.get()],
            ),
        )
        button.grid(row=len(input_plan.options) + 1, column=1, sticky="w", padx=6)

    def _submit(self, plan: WidgetPlan, value: JsonValue = None) -> None:
        submission = collect_submission(plan, value)
        self.submissions.append(submission)
        print(json.dumps(submission.as_transport(), sort_keys=True))


def launch_fixture(path: Path) -> TkReferenceApp:
    """Render a fixture in a live Tkinter window."""

    import tkinter as tk

    document = render_fixture_document(load_fixture(path))
    root = tk.Tk()
    app = TkReferenceApp(root, document)
    root.mainloop()
    return app


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="Path to a conformance fixture JSON file")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print the widget plan and sample submissions instead of opening Tk.",
    )
    args = parser.parse_args(argv)

    if args.inspect:
        print(json.dumps(inspect_fixture(args.fixture), indent=2, sort_keys=True))
    else:
        launch_fixture(args.fixture)
    return 0


def _choice_input_plan(
    choice: ChoiceControl,
    pieces_by_zone: Mapping[str, tuple[PieceOption, ...]],
) -> InputControlPlan | None:
    kind = choice.accepts_kind or "pick"
    accepts = choice.accepts or {}
    if kind == "pick":
        return InputControlPlan(kind="pick", widget="button")
    if kind in {"text", "raw_command"}:
        return InputControlPlan(kind=kind, widget="entry", payload_key="text")
    if kind == "quantity":
        return InputControlPlan(
            kind=kind,
            widget="spinbox",
            payload_key="quantity",
            minimum=_optional_int(accepts.get("min")),
            maximum=_optional_int(accepts.get("max")),
            step=_optional_int(accepts.get("step")),
            unit=_optional_text(accepts.get("unit")),
        )
    if kind == "pieces":
        constraints = accepts.get("constraints")
        zone_ref = None
        if isinstance(constraints, dict):
            zone_ref = _optional_text(constraints.get("target_zone_ref"))
        return InputControlPlan(
            kind=kind,
            widget="piece_selector",
            payload_key="piece_ids",
            minimum=_optional_int(accepts.get("min")),
            maximum=_optional_int(accepts.get("max")),
            options=pieces_by_zone.get(zone_ref or "", ()),
        )
    if kind == "place":
        constraints = accepts.get("constraints")
        source_zone_ref = _optional_text(accepts.get("source_zone_ref"))
        target_zone_ref = _optional_text(accepts.get("target_zone_ref"))
        if isinstance(constraints, dict):
            source_zone_ref = source_zone_ref or _optional_text(
                constraints.get("source_zone_ref")
            )
            target_zone_ref = target_zone_ref or _optional_text(
                constraints.get("target_zone_ref")
            )
        return InputControlPlan(
            kind=kind,
            widget="place_selector",
            payload_key="piece_id",
            minimum=1,
            maximum=1,
            source_zone_ref=source_zone_ref,
            target_zone_ref=target_zone_ref,
            options=pieces_by_zone.get(source_zone_ref or "", ()),
        )
    return InputControlPlan(kind=kind, widget="button")


def _piece_options_by_zone(document: RenderDocument) -> dict[str, tuple[PieceOption, ...]]:
    zones: dict[str, list[PieceOption]] = {}
    current_zone: str | None = None
    zone_indent = 0

    for item in document.items:
        if item.role == "zone_label" and item.ref_id:
            current_zone = item.ref_id
            zone_indent = item.indent
            zones.setdefault(current_zone, [])
            continue
        if current_zone is not None and item.indent <= zone_indent and item.role != "piece":
            current_zone = None
        if item.role != "piece":
            continue

        zone_ref = _item_text(item.data, "zone_ref") or current_zone
        if zone_ref is None:
            continue
        option = PieceOption(
            value=_item_text(item.data, "piece_id") or item.ref_id or item.text,
            label=_item_text(item.data, "label") or _piece_label(item.text),
            ref_id=item.ref_id,
            zone_ref=zone_ref,
        )
        if all(existing.value != option.value for existing in zones.setdefault(zone_ref, [])):
            zones[zone_ref].append(option)

    return {zone_ref: tuple(options) for zone_ref, options in zones.items()}


def _validate_piece_selection(input_plan: InputControlPlan, piece_ids: list[str]) -> None:
    valid_ids = {option.value for option in input_plan.options}
    invalid_ids = [piece_id for piece_id in piece_ids if piece_id not in valid_ids]
    if invalid_ids:
        raise ValueError(f"Unknown piece selection: {', '.join(invalid_ids)}")
    if input_plan.minimum is not None and len(piece_ids) < input_plan.minimum:
        raise ValueError(f"Select at least {input_plan.minimum} piece(s)")
    if input_plan.maximum is not None and len(piece_ids) > input_plan.maximum:
        raise ValueError(f"Select at most {input_plan.maximum} piece(s)")


def _selected_piece_ids(value: JsonValue) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return cast(list[str], value)
    raise ValueError("Piece choices require a piece id or list of piece ids")


def _sample_submission(plan: WidgetPlan) -> Submission | None:
    if plan.input is None or plan.input.kind == "pick":
        return collect_submission(plan)
    if plan.input.kind in {"text", "raw_command"}:
        return collect_submission(plan, "sample")
    if plan.input.kind == "quantity":
        return collect_submission(plan, plan.input.minimum or 1)
    if plan.input.kind == "pieces" and plan.input.options:
        return collect_submission(plan, [plan.input.options[0].value])
    if plan.input.kind == "place" and plan.input.options:
        return collect_submission(plan, plan.input.options[0].value)
    return None


def _widget_plan_json(plan: WidgetPlan) -> JsonObject:
    return {
        "role": plan.role,
        "widget": plan.widget,
        "text": plan.text,
        "ref_id": plan.ref_id,
        "enabled": plan.enabled,
        "accepts_kind": plan.choice.accepts_kind if plan.choice else None,
        "edge_id": plan.choice.edge_id if plan.choice else None,
        "input": _input_plan_json(plan.input) if plan.input else None,
    }


def _input_plan_json(plan: InputControlPlan | None) -> JsonObject | None:
    if plan is None:
        return None
    return {
        "kind": plan.kind,
        "widget": plan.widget,
        "payload_key": plan.payload_key,
        "minimum": plan.minimum,
        "maximum": plan.maximum,
        "step": plan.step,
        "unit": plan.unit,
        "source_zone_ref": plan.source_zone_ref,
        "target_zone_ref": plan.target_zone_ref,
        "options": [
            {
                "value": option.value,
                "label": option.label,
                "ref_id": option.ref_id,
                "zone_ref": option.zone_ref,
            }
            for option in plan.options
        ],
    }


def _int_value(value: JsonValue) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError("Quantity choices require an integer")


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _item_text(data: JsonObject | None, key: str) -> str | None:
    if data is None:
        return None
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _piece_label(text: str) -> str:
    label = text.removeprefix("- ").strip()
    if " [" in label:
        label = label.rsplit(" [", 1)[0]
    return label


def _quantity_bounds_text(plan: InputControlPlan) -> str:
    unit = f" {plan.unit}" if plan.unit else ""
    if plan.minimum is not None and plan.maximum is not None:
        return f"{plan.minimum}-{plan.maximum}{unit}"
    if plan.minimum is not None:
        return f">= {plan.minimum}{unit}"
    if plan.maximum is not None:
        return f"<= {plan.maximum}{unit}"
    return unit.strip()


def _tk_state(plan: WidgetPlan) -> str:
    return "normal" if plan.enabled else "disabled"


if __name__ == "__main__":
    raise SystemExit(main())
