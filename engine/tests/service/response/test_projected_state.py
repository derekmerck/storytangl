from __future__ import annotations

import pytest

from tangl.journal.fragments import PresentationHints
from tangl.service.response import (
    BadgeListValue,
    ItemListValue,
    KvListValue,
    ProjectedItem,
    ProjectedKVItem,
    ProjectedSection,
    ProjectedState,
    ScalarValue,
    TableValue,
)


def _fixture() -> ProjectedState:
    return ProjectedState(
        sections=[
            ProjectedSection(
                section_id="stats",
                title="Stats",
                kind="stats",
                value=KvListValue(
                    items=[
                        ProjectedKVItem(key="Health", value=9),
                        ProjectedKVItem(key="Gold", value=14),
                    ]
                ),
            ),
            ProjectedSection(
                section_id="inventory",
                title="Inventory",
                kind="inventory",
                value=ItemListValue(
                    items=[
                        ProjectedItem(label="Lantern", detail="Lit", tags=["equipped"]),
                        ProjectedItem(label="Key", tags=["quest"]),
                    ]
                ),
                hints=PresentationHints(style_name="sidebar"),
            ),
            ProjectedSection(
                section_id="quests",
                title="Quests",
                kind="quest_log",
                value=TableValue(
                    columns=["Quest", "Status"],
                    rows=[["Find the key", "active"], ["Open the vault", "locked"]],
                ),
            ),
            ProjectedSection(
                section_id="flags",
                title="Flags",
                kind="flags",
                value=BadgeListValue(items=["torch_lit", "met_guide"]),
            ),
            ProjectedSection(
                section_id="weight",
                title="Weight",
                kind="custom_metrics",
                value=ScalarValue(value=12.5),
            ),
        ]
    )


def _render_cli(state: ProjectedState) -> list[str]:
    lines: list[str] = []
    for section in state.sections:
        lines.append(section.title)
        value = section.value
        if isinstance(value, KvListValue):
            lines.extend(f"{item.key}: {item.value}" for item in value.items)
        elif isinstance(value, ItemListValue):
            lines.extend(item.label for item in value.items)
        elif isinstance(value, TableValue):
            lines.extend(" | ".join(str(cell) for cell in row) for row in value.rows)
        elif isinstance(value, BadgeListValue):
            lines.append(", ".join(value.items))
        elif isinstance(value, ScalarValue):
            lines.append(str(value.value))
    return lines


def _render_web_payload(state: ProjectedState) -> list[dict[str, object]]:
    return [section.model_dump(mode="python") for section in state.sections]


def test_projected_state_round_trips_through_model_dump_and_validate() -> None:
    state = _fixture()

    payload = state.model_dump(mode="python")
    restored = ProjectedState.model_validate(payload)

    assert restored == state


def test_projected_state_preserves_section_order() -> None:
    state = _fixture()

    assert [section.section_id for section in state.sections] == [
        "stats",
        "inventory",
        "quests",
        "flags",
        "weight",
    ]


def test_projected_state_preserves_custom_kind_strings() -> None:
    state = _fixture()

    assert state.sections[2].kind == "quest_log"
    assert state.sections[4].kind == "custom_metrics"


def test_cliish_adapter_renders_ordered_sections_without_graph_access() -> None:
    lines = _render_cli(_fixture())

    assert lines[:4] == ["Stats", "Health: 9", "Gold: 14", "Inventory"]
    assert "Lantern" in lines
    assert "Find the key | active" in lines


def test_webish_adapter_produces_json_ready_section_blocks() -> None:
    payload = _render_web_payload(_fixture())

    assert payload[0]["section_id"] == "stats"
    assert payload[1]["hints"]["style_name"] == "sidebar"
    assert payload[2]["value"]["value_type"] == "table"
    assert payload[4]["kind"] == "custom_metrics"


def test_table_value_rejects_rows_with_wrong_width() -> None:
    with pytest.raises(ValueError, match="table row 1 has 1 values but expected 2"):
        TableValue(
            columns=["Quest", "Status"],
            rows=[["Find the key", "active"], ["locked"]],
        )
