"""Generate backend-emitted widget contract diagnostics.

The saved diagnostics in this directory are deliberately not canonical
conformance fixtures. They prove that the current service layer can emit
widget-shaped data before a genre demo, such as CarWars, tries to consume it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from tangl.persistence import PersistenceManagerFactory
from tangl.service import (
    BadgeListValue,
    InfoAffordance,
    ItemListValue,
    KvListValue,
    KvRow,
    ProjectedItem,
    ProjectedSection,
    ProjectedState,
    ScalarValue,
    ServiceManager,
    TableValue,
)
from tangl.service.user.user import User
from tangl.story import InitMode, World
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.runtime.ledger import Ledger


DIAGNOSTIC_DIR = Path(__file__).parent / "diagnostics"
RUNTIME_FIXTURE = DIAGNOSTIC_DIR / "backend_widget_contract_runtime.json"
PROJECTED_FIXTURE = DIAGNOSTIC_DIR / "backend_widget_contract_projected_state.json"

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class _WidgetDemoProjector:
    """Project generic widget-contract state without bundle-specific concepts."""

    def project(self, *, ledger: Ledger) -> ProjectedState:
        return ProjectedState(
            sections=[
                ProjectedSection(
                    section_id="session",
                    title="Session",
                    kind="stats",
                    value=KvListValue(
                        items=[
                            KvRow(key="Cursor", value=ledger.cursor.label),
                            KvRow(key="Step", value=ledger.step),
                        ],
                    ),
                ),
                ProjectedSection(
                    section_id="supplies",
                    title="Supplies",
                    kind="resource",
                    value=KvListValue(
                        items=[
                            KvRow(key="Rations", value=2, max=6, hint="bar"),
                            KvRow(key="Coin", value=14, unit="silver"),
                        ],
                    ),
                ),
                ProjectedSection(
                    section_id="inventory",
                    title="Inventory",
                    kind="inventory",
                    value=ItemListValue(
                        items=[
                            ProjectedItem(label="Lantern", detail="half-oil", tags=["light"]),
                            ProjectedItem(label="Road map", tags=["route"]),
                        ],
                    ),
                ),
                ProjectedSection(
                    section_id="watch",
                    title="Watch",
                    kind="roster",
                    value=TableValue(
                        columns=["Name", "Role"],
                        rows=[["Mira", "Scout"], ["Tovin", "Guard"]],
                    ),
                ),
                ProjectedSection(
                    section_id="conditions",
                    title="Conditions",
                    kind="tags",
                    value=BadgeListValue(items=["rain", "night"]),
                ),
                ProjectedSection(
                    section_id="danger",
                    title="Danger",
                    kind="status",
                    value=ScalarValue(value="low"),
                ),
            ],
        )


def _script_data() -> dict[str, object]:
    return {
        "label": "widget_contract_demo",
        "metadata": {
            "title": "Widget Contract Demo",
            "author": "StoryTangl",
            "start_at": "intro.start",
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "The road forks under cold rain.",
                        "actions": [
                            {
                                "text": "Buy rations.",
                                "successor": "market",
                                "accepts": {
                                    "kind": "quantity",
                                    "min": 1,
                                    "max": 3,
                                    "unit": "ration",
                                },
                                "ui_hints": {
                                    "hotkey": "b",
                                    "source_kind": "market",
                                    "contribution": "purchase",
                                },
                            },
                            {
                                "text": "Name the mule.",
                                "successor": "market",
                                "accepts": {
                                    "kind": "text",
                                    "placeholder": "Buttercup",
                                },
                                "ui_hints": {
                                    "hotkey": "n",
                                    "source_kind": "stable",
                                    "contribution": "rename",
                                },
                            },
                        ],
                    },
                    "market": {
                        "content": "The quartermaster marks the ledger.",
                    },
                },
            },
        },
    }


def _advertise_info_channels(
    caller: object,
    *,
    ctx: PhaseCtx,
) -> list[InfoAffordance]:
    _ = (caller, ctx)
    return [
        InfoAffordance(
            kind="inventory",
            label="Inventory",
            shortcuts=["i", "inv"],
            query={"kinds": ["inventory"]},
        ),
        InfoAffordance(
            kind="map",
            label="Map",
            shortcuts=["m"],
            query={"kinds": ["map"], "format": "text"},
        ),
    ]


def build_demo_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return normalized JSON-ready RuntimeEnvelope and ProjectedState payloads."""

    World.clear_instances()
    try:
        persistence = PersistenceManagerFactory.native_in_mem()
        manager = ServiceManager(persistence)
        user = User(label="widget-contract-user")
        persistence.save(user)

        world = World.from_script_data(
            script_data=_script_data(),
            story_info_projector=_WidgetDemoProjector(),
        )
        world.dispatch.register(
            _advertise_info_channels,
            task="advertise_info_channels",
        )

        envelope = manager.create_story(
            user_id=user.uid,
            world_id=world.label,
            world=world,
            init_mode=InitMode.EAGER.value,
            story_label="widget_contract_story",
        )
        projected = manager.get_story_info(user_id=user.uid)

        runtime_payload = envelope.to_dto()
        projected_payload = projected.to_dto()
        return _normalize_uuids(runtime_payload), _normalize_uuids(projected_payload)
    finally:
        World.clear_instances()


def write_demo_payloads(directory: Path = DIAGNOSTIC_DIR) -> tuple[Path, Path]:
    """Write the current backend-emitted diagnostic payloads."""

    runtime_payload, projected_payload = build_demo_payloads()
    directory.mkdir(parents=True, exist_ok=True)
    runtime_path = directory / RUNTIME_FIXTURE.name
    projected_path = directory / PROJECTED_FIXTURE.name
    _write_json(runtime_path, runtime_payload)
    _write_json(projected_path, projected_payload)
    return runtime_path, projected_path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _normalize_uuids(payload: Any) -> Any:
    seen: dict[str, str] = {}

    def normalize(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, str) and _UUID_PATTERN.fullmatch(value):
            if value not in seen:
                seen[value] = str(uuid5(NAMESPACE_URL, f"storytangl-widget-demo:{len(seen) + 1}"))
            return seen[value]
        return value

    return normalize(payload)


if __name__ == "__main__":
    runtime_path, projected_path = write_demo_payloads()
    print(runtime_path)
    print(projected_path)
