from __future__ import annotations

import pytest

from tangl.presentation.hints import PresentationHints
from tangl.presentation.projection import (
    BadgeListValue,
    InfoAffordance,
    InfoState,
    ItemListValue,
    KvListValue,
    ProjectedItem,
    ProjectedSection,
    ProjectedState,
    ScalarValue,
    StoryInfoRequest,
    TableValue,
)
from tangl.presentation.values import KvRow


def _fixture() -> ProjectedState:
    return ProjectedState(
        sections=[
            ProjectedSection(
                section_id="stats",
                title="Stats",
                kind="stats",
                value=KvListValue(
                    items=[KvRow(key="Health", value=9), KvRow(key="Gold", value=14)]
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


def test_projected_state_round_trips_through_model_dump_and_validate() -> None:
    state = _fixture()

    assert ProjectedState.model_validate(state.model_dump(mode="python")) == state


def test_projected_state_to_dto_preserves_value_discriminators() -> None:
    state = _fixture()
    payload = state.to_dto()

    assert payload["sections"][0]["value"]["value_type"] == "kv_list"
    assert payload["sections"][1]["hints"]["style_name"] == "sidebar"
    assert payload["sections"][2]["value"]["value_type"] == "table"
    assert payload["sections"][4]["value"]["value_type"] == "scalar"
    assert ProjectedState.model_validate(payload) == state


def test_projected_state_preserves_section_order_and_custom_kinds() -> None:
    state = _fixture()

    assert [section.section_id for section in state.sections] == [
        "stats",
        "inventory",
        "quests",
        "flags",
        "weight",
    ]
    assert state.sections[2].kind == "quest_log"
    assert state.sections[4].kind == "custom_metrics"


def test_adapters_can_render_ordered_sections_without_graph_access() -> None:
    state = _fixture()
    lines = [
        item.label if isinstance(section.value, ItemListValue) else section.title
        for section in state.sections
        for item in (section.value.items if isinstance(section.value, ItemListValue) else [section])
    ]

    assert lines == ["Stats", "Lantern", "Key", "Quests", "Flags", "Weight"]
    assert [section.model_dump(mode="python") for section in state.sections][1]["hints"][
        "style_name"
    ] == "sidebar"


def test_table_value_rejects_rows_with_wrong_width() -> None:
    with pytest.raises(ValueError, match="table row 1 has 1 values but expected 2"):
        TableValue(
            columns=["Quest", "Status"],
            rows=[["Find the key", "active"], ["locked"]],
        )


def test_info_affordance_and_state_are_json_ready_contract_models() -> None:
    affordance = InfoAffordance(
        kind="map",
        label="Map",
        shortcuts=["m"],
        query={"type": "map", "scope": "known"},
    )
    state = InfoState(version=7, dirty_kinds=["map"], available_kinds=["map", "inventory"])

    assert affordance.model_dump(mode="python") == {
        "kind": "map",
        "label": "Map",
        "shortcuts": ["m"],
        "query": {"type": "map", "scope": "known"},
    }
    assert state.model_dump(mode="python") == {
        "version": 7,
        "dirty_kinds": ["map"],
        "available_kinds": ["map", "inventory"],
    }


def test_story_info_request_gathers_explicit_and_opaque_query_kinds() -> None:
    request = StoryInfoRequest(
        kind="status",
        kinds=["inventory"],
        query={"kinds": ["location", "presence"], "type": "map"},
    )

    assert request.requested_kinds() == ["status", "inventory", "location", "presence"]
