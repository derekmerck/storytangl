"""Executable checks for the bounded presentation-realization diagnostic."""

from __future__ import annotations

import json
import re

import pytest

pytest.importorskip("rich")

from rich.text import Text

from engine.contrib.conformance.presentation_realization_demo import (
    DEFAULT_TERMINAL_STYLES,
    OFFSET_UNIT,
    SOURCE_PATHS,
    adapt_authored_bundle,
    build_report,
    normalize_bundle,
    parse_pandoc_markup,
    readable_text,
    realize_html,
    realize_terminal,
    safe_class_token,
    structural_manifest,
)


@pytest.fixture(scope="module")
def sources() -> list[dict[str, object]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in SOURCE_PATHS]


def test_all_realizations_preserve_readable_text_and_structure(
    sources: list[dict[str, object]],
) -> None:
    for source in sources:
        normalized = normalize_bundle(source)
        expected_text = readable_text(normalized)
        expected_manifest = structural_manifest(normalized)
        html_stage = realize_html(normalized)
        rich_text, terminal_stage = realize_terminal(normalized)

        assert isinstance(rich_text, Text)
        assert html_stage["plain_text"] == expected_text
        assert terminal_stage["rich_plain"] == expected_text
        assert terminal_stage["no_color"] == expected_text
        assert html_stage["manifest"] == expected_manifest
        assert terminal_stage["manifest"] == expected_manifest


def test_normalization_touches_only_explicit_text_fields(
    sources: list[dict[str, object]],
) -> None:
    mixed = normalize_bundle(sources[1])
    content = mixed["fragments"][0]

    assert content["content"] == {
        "text": "Bridge watch: hard rain",
        "spans": [],
        "offset_unit": OFFSET_UNIT,
    }
    assert content["debug_payload"] == {
        "text": "**not eligible** <unsafe>",
        "nested": {"content": "{{ untouched }}"},
    }
    assert "not eligible" not in realize_html(mixed)["markup"]


def test_unknown_tokens_degrade_without_losing_content(
    sources: list[dict[str, object]],
) -> None:
    normalized = normalize_bundle(sources[0])
    rich_text, terminal = realize_terminal(normalized)

    assert "Keep your <lantern> lit." in rich_text.plain
    assert all(
        "unknown:glimmer" not in span["style"]
        for span in terminal["rich_spans"]
    )
    assert safe_class_token("unknown:glimmer") in realize_html(normalized)["markup"]


def test_html_escapes_text_and_keeps_structural_annotations_outside_spans(
    sources: list[dict[str, object]],
) -> None:
    prose_html = realize_html(normalize_bundle(sources[0]))["markup"]
    packet_html = realize_html(normalize_bundle(sources[1]))["markup"]
    admonition_class = safe_class_token("block:admonition")
    packet_class = safe_class_token("group:status_packet")

    assert "&lt;lantern&gt;" in prose_html
    assert "<lantern>" not in prose_html
    assert '<aside data-fragment-id="10000000-0000-0000-0000-000000000001"' in prose_html
    assert f'class="{admonition_class}' in prose_html
    assert '<div data-fragment-id="20000000-0000-0000-0000-000000000005"' in packet_html
    assert f'class="{packet_class}' in packet_html
    assert f'<span class="{admonition_class}' not in prose_html
    assert f'<span class="{packet_class}' not in packet_html

    injected_event_id = normalize_bundle(sources[1])
    injected_event_id["ux_events"][0]["event_id"] = 'event" onclick="unsafe'
    injected_html = realize_html(injected_event_id)["markup"]
    assert 'data-event-id="event&quot; onclick=&quot;unsafe"' in injected_html
    assert 'data-event-id="event" onclick="unsafe"' not in injected_html


def test_safe_class_tokens_are_injective_for_namespaces() -> None:
    tokens = [
        ":",
        "_3a",
        "_",
        "é",
        "🌩",
        "",
        "speaker:guide",
        "speaker-guide",
    ]
    classes = [safe_class_token(token) for token in tokens]

    assert len(set(classes)) == len(tokens)
    assert safe_class_token(":") != safe_class_token("_3a")
    assert safe_class_token("speaker:guide") != safe_class_token("speaker-guide")
    assert all(re.fullmatch(r"st-x[0-9a-f]*", value) for value in classes)


def test_authoring_adapter_separates_literal_markup_from_neutral_offsets(
    sources: list[dict[str, object]],
) -> None:
    normalized, adapter = adapt_authored_bundle(sources[0])
    authored_markup = sources[0]["fragments"][0]["authored_markup"]
    trace = adapter["fragments"][0]
    content = normalized["fragments"][0]["content"]

    assert "{{ reader }}" in authored_markup
    assert "{% if storm %}" in authored_markup
    assert "[" in authored_markup and "]{.inline:emphasis}" in authored_markup
    assert authored_markup.startswith("::: {.block:admonition .tone:warning}")
    assert "{{ reader }}" not in trace["evaluated_markup"]
    assert trace["neutral_text"] == content
    assert content["offset_unit"] == OFFSET_UNIT
    assert content["spans"][0]["end"] == content["spans"][1]["start"]


def test_scalar_offsets_expose_javascript_utf16_mismatch(
    sources: list[dict[str, object]],
) -> None:
    content = normalize_bundle(sources[0])["fragments"][0]["content"]
    first_span = content["spans"][0]
    prefix = content["text"][: first_span["start"]]

    assert "🌩" in prefix
    assert len(prefix) == first_span["start"]
    assert len(prefix.encode("utf-16-le")) // 2 == first_span["start"] + 1


def test_diagnostic_span_grammar_rejects_nested_and_overlapping_spans() -> None:
    with pytest.raises(ValueError, match="Nested, overlapping"):
        parse_pandoc_markup(
            "::: {.block:note}\n[outer [inner]{.inline:a}]{.inline:b}\n:::",
            {},
        )

    overlapping = {
        "fragments": [
            {
                "uid": "overlap",
                "fragment_type": "content",
                "content": {
                    "text": "abcdef",
                    "offset_unit": OFFSET_UNIT,
                    "spans": [
                        {"start": 0, "end": 4, "tokens": ["inline:a"]},
                        {"start": 2, "end": 6, "tokens": ["inline:b"]},
                    ],
                },
            }
        ],
        "ux_events": [],
    }
    with pytest.raises(ValueError, match="flat and non-overlapping"):
        realize_html(overlapping)


def test_canonical_dto_is_independent_of_terminal_theme(
    sources: list[dict[str, object]],
) -> None:
    normalized = normalize_bundle(sources[0])
    alternate_styles = {**DEFAULT_TERMINAL_STYLES, "speaker:guide": "magenta"}

    _, default_terminal = realize_terminal(normalized)
    _, alternate_terminal = realize_terminal(normalized, styles=alternate_styles)

    assert normalize_bundle(sources[0]) == normalized
    assert default_terminal["rich_plain"] == alternate_terminal["rich_plain"]
    assert default_terminal["rich_spans"] != alternate_terminal["rich_spans"]


def test_mixed_packet_retains_identity_provenance_and_event_placement(
    sources: list[dict[str, object]],
) -> None:
    normalized = normalize_bundle(sources[1])
    manifest = structural_manifest(normalized)
    media = normalized["fragments"][3]
    _, terminal = realize_terminal(normalized)

    assert manifest["fragment_order"] == [
        "20000000-0000-0000-0000-000000000001",
        "20000000-0000-0000-0000-000000000002",
        "20000000-0000-0000-0000-000000000003",
        "20000000-0000-0000-0000-000000000004",
        "20000000-0000-0000-0000-000000000005",
    ]
    assert manifest["provenance"]["20000000-0000-0000-0000-000000000001"] == {
        "origin_id": "20000000-0000-0000-0000-000000000101",
        "source_id": "20000000-0000-0000-0000-000000000201",
    }
    assert manifest["choices"] == [
        {
            "uid": "20000000-0000-0000-0000-000000000003",
            "edge_id": "20000000-0000-0000-0000-000000000303",
            "available": False,
            "unavailable_reason": "Gate closed",
        }
    ]
    assert manifest["media_fallbacks"] == {
        "20000000-0000-0000-0000-000000000004": (
            "The bridge disappears into hard rain."
        )
    }
    assert media["media_role"] == "narrative_im"
    assert any(
        terminal["rich_plain"][span["start"] : span["end"]].startswith("x) Cross")
        and "dim" in span["style"]
        for span in terminal["rich_spans"]
    )
    assert manifest["groups"]["20000000-0000-0000-0000-000000000005"] == [
        "20000000-0000-0000-0000-000000000001",
        "20000000-0000-0000-0000-000000000002",
        "20000000-0000-0000-0000-000000000003",
        "20000000-0000-0000-0000-000000000004",
    ]
    assert manifest["ux_event_order"] == [
        "20000000-0000-0000-0000-000000000401"
    ]


def test_report_keeps_all_realization_stages_inspectable() -> None:
    report = build_report()
    matrix = report["projection_realization_matrix"]

    assert report["status"] == "experimental"
    assert matrix["bundle_positions"] == {
        "prose-dialog": ["typed-neutral-fragments", "attributed-neutral-text"],
        "mixed-packet": ["typed-neutral-fragments"],
    }
    assert matrix["points"][-1]["status"] == (
        "valid ephemeral realization of a stored typed packet"
    )
    assert [stage["stage"] for stage in matrix["authority_chain"]] == [
        "graph",
        "journal-phase",
        "journal-registry",
        "transport",
        "client",
    ]
    assert "normal action contract" in matrix["client_boundaries"]["prose_blind_bot"]
    assert matrix["replay_contract"][-1].startswith("exact rendition replay is optional")
    assert [bundle["bundle_id"] for bundle in report["bundles"]] == [
        "prose-dialog",
        "mixed-packet",
    ]
    for bundle in report["bundles"]:
        assert {
            "authored",
            "authoring_adapter",
            "normalized",
            "html",
            "terminal",
            "plain_fallback",
        } <= set(bundle)
    assert "\x1b" not in json.dumps(report)
