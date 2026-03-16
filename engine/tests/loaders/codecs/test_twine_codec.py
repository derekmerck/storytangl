"""Tests for the bundled Twee 3 codec.

Organized by behavior:
- Parsing helpers: slugging, header parsing, and macro classification.
- Decode behavior: supported subset mapping and structured loss records.
- Registry wiring: bundled aliases resolve to the Twine codec.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tangl.loaders import CodecRegistry, LossKind, WorldBundle
from tangl.loaders.codecs.twine import (
    FEATURE_MACROS_IF,
    FEATURE_SPECIAL_PASSAGE,
    ISSUE_DANGLING_LINK,
    ISSUE_DUPLICATE_PASSAGE,
    ISSUE_INVALID_STORY_DATA,
    ISSUE_SLUG_COLLISION,
    TwineCodec,
    _classify_macro,
    _parse_twee,
    _slugify,
)


def _write_bundle(
    tmp_path: Path,
    *,
    label: str = "twine_unit",
    scripts: dict[str, str],
    codec: str = "twee3_1_0",
) -> WorldBundle:
    root = tmp_path / label
    root.mkdir()

    script_names = list(scripts.keys())
    if len(script_names) == 1:
        scripts_value = script_names[0]
    else:
        scripts_value = "\n".join(f"  - {name}" for name in script_names)

    (root / "world.yaml").write_text(
        (
            f"label: {label}\n"
            f"codec: {codec}\n"
            f"scripts: {scripts_value}\n"
        ),
        encoding="utf-8",
    )
    for script_name, script_text in scripts.items():
        (root / script_name).write_text(script_text.strip(), encoding="utf-8")

    return WorldBundle.load(root)


def _decode_bundle(bundle: WorldBundle):
    return TwineCodec().decode(
        bundle=bundle,
        script_paths=bundle.get_script_paths(),
        story_key=None,
    )


class TestTwineHelpers:
    """Tests for helper behavior that shapes Twine decode output."""

    def test_slugify_normalizes_basic_text(self) -> None:
        assert _slugify("The Ruined Tower") == "the_ruined_tower"

    def test_slugify_ascii_fallback_uses_passage(self) -> None:
        assert _slugify("---") == "passage"

    def test_slugify_normalizes_unicode(self) -> None:
        assert _slugify("Cafe noir") == "cafe_noir"

    def test_parse_twee_extracts_tags_meta_and_body(self) -> None:
        passages = _parse_twee(
            source="""
:: Start [entry hub] {"position":"0,0"}
Hello there.

:: Next
Goodbye.
            """.strip(),
            path=Path("story.twee"),
            start_ordinal=0,
        )

        assert len(passages) == 2
        assert passages[0].name == "Start"
        assert passages[0].tags == ["entry", "hub"]
        assert passages[0].meta == {"position": "0,0"}
        assert passages[0].body == "Hello there."
        assert passages[1].name == "Next"

    def test_classify_macro_groups_if_family(self) -> None:
        assert _classify_macro("<<elseif $torch>>") == FEATURE_MACROS_IF


class TestTwineDecode:
    """Tests for decoding supported Twee content and reporting losses."""

    def test_decode_maps_supported_links_title_and_start(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: StoryTitle
The Ruined Tower

:: StoryData
{"start":"Start","format":"Twine 2","format-version":"2.0"}

:: Start [entry]
Choose your path.
[[Inside]]
[[Look closer->Look]]
[[Take the road|Road]]

:: Inside
Inside.

:: Look
Look.

:: Road
Road.
                """
            },
        )

        result = _decode_bundle(bundle)
        blocks = result.story_data["scenes"]["world"]["blocks"]
        actions = blocks["start"]["actions"]

        assert result.story_data["metadata"]["title"] == "The Ruined Tower"
        assert result.story_data["metadata"]["start_at"] == "world.start"
        assert result.codec_state["story_format"] == "Twine 2"
        assert result.codec_state["story_format_version"] == "2.0"
        assert blocks["start"]["tags"] == ["entry"]
        assert [action["text"] for action in actions] == [
            "Inside",
            "Look closer",
            "Take the road",
        ]
        assert [action["successor_ref"] for action in actions] == [
            "inside",
            "look",
            "road",
        ]
        assert result.loss_records == []
        assert result.warnings == []

    def test_decode_reports_duplicate_passage_and_keeps_latest_definition(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: Start
Old text.

:: Start
New text.
                """
            },
        )

        result = _decode_bundle(bundle)

        assert result.story_data["scenes"]["world"]["blocks"]["start"]["content"] == "New text."
        assert any(record.feature == ISSUE_DUPLICATE_PASSAGE for record in result.loss_records)

    def test_decode_suffixes_slug_collisions_for_distinct_surviving_names(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: A B
One.

:: A-B
Two.
                """
            },
        )

        result = _decode_bundle(bundle)
        blocks = result.story_data["scenes"]["world"]["blocks"]

        assert set(blocks.keys()) == {"a_b", "a_b_2"}
        assert any(record.feature == ISSUE_SLUG_COLLISION for record in result.loss_records)

    def test_decode_reports_invalid_story_data(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: StoryData
{not json}

:: Start
Hello.
                """
            },
        )

        result = _decode_bundle(bundle)

        assert any(record.feature == ISSUE_INVALID_STORY_DATA for record in result.loss_records)
        assert result.story_data["metadata"]["start_at"] == "world.start"

    def test_decode_reports_unsupported_special_passages(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: StoryStylesheet
body { color: red; }

:: Start
Hello.
                """
            },
        )

        result = _decode_bundle(bundle)

        assert "storystylesheet" not in result.story_data["scenes"]["world"]["blocks"]
        assert any(
            record.kind is LossKind.UNSUPPORTED_FEATURE and record.feature == FEATURE_SPECIAL_PASSAGE
            for record in result.loss_records
        )

    def test_decode_lowers_simple_set_macro_into_block_effects(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: Begin
<<set $gold to 1>>
Ready.

:: End
Done.
                """
            },
        )

        result = _decode_bundle(bundle)
        begin = result.story_data["scenes"]["world"]["blocks"]["begin"]

        assert begin["content"] == "Ready."
        assert begin["effects"] == ["self.graph.locals['gold'] = 1"]
        assert result.loss_records == []
        assert result.warnings == []

    def test_decode_lowers_conditional_links_and_setters_into_generated_blocks(
        self,
        tmp_path: Path,
    ) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: Begin
<<if $gold is 1>>[[Spend->End][$gold += 1]]<<else>>[[Wait->Elsewhere]]<<endif>>

:: End
Done.

:: Elsewhere
Else.
                """
            },
        )

        result = _decode_bundle(bundle)
        blocks = result.story_data["scenes"]["world"]["blocks"]
        begin = blocks["begin"]
        spend_action = next(action for action in begin["actions"] if action["text"] == "Spend")
        wait_action = next(action for action in begin["actions"] if action["text"] == "Wait")
        spend_gate = blocks[spend_action["successor_ref"]]
        wait_gate = blocks[wait_action["successor_ref"]]

        assert spend_action["successor_ref"].startswith("begin__link_")
        assert spend_gate["is_anonymous"] is True
        assert spend_gate["continues"][0]["successor_ref"] == "end"
        assert spend_gate["effects"] == [
            "self.graph.locals['gold'] = self.graph.locals.get('gold', 0) + (1)"
        ]
        assert spend_gate["availability"] == [{"expr": "(self.graph.locals.get('gold') == 1)"}]
        assert wait_gate["continues"][0]["successor_ref"] == "elsewhere"
        assert wait_gate["availability"] == [
            {"expr": "not (self.graph.locals.get('gold') == 1)"}
        ]
        assert result.codec_state["generated_block_count"] == 2
        assert result.loss_records == []

    def test_decode_reports_conditional_prose_as_unsupported_if(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: Begin
<<if $torch>>Lit<<endif>> [[Go->End]]

:: End
Done.
                """
            },
        )

        result = _decode_bundle(bundle)
        begin = result.story_data["scenes"]["world"]["blocks"]["begin"]

        assert begin["content"] == ""
        assert begin["actions"][0]["successor_ref"] == "end"
        assert any(record.feature == FEATURE_MACROS_IF for record in result.loss_records)
        assert any("loss records" in warning for warning in result.warnings)

    def test_decode_reports_dangling_links_as_authoring_debt(self, tmp_path: Path) -> None:
        bundle = _write_bundle(
            tmp_path,
            scripts={
                "story.twee": """
:: Start
[[Go->Missing]]
                """
            },
        )

        result = _decode_bundle(bundle)
        action = result.story_data["scenes"]["world"]["blocks"]["start"]["actions"][0]

        assert action["successor_ref"] == "missing"
        assert any(
            record.kind is LossKind.AUTHORING_DEBT and record.feature == ISSUE_DANGLING_LINK
            for record in result.loss_records
        )


class TestTwineCodecRegistry:
    """Tests for bundled codec registration and import-only behavior."""

    def test_registry_resolves_all_twine_aliases_to_same_instance(self) -> None:
        registry = CodecRegistry()
        codec = registry.get("twine")

        assert registry.get("twee") is codec
        assert registry.get("twee3") is codec
        assert registry.get("twee3_1_0") is codec
        assert codec.codec_id == "twee3_1_0"

    def test_encode_is_explicitly_unsupported_in_v1(self) -> None:
        with pytest.raises(NotImplementedError, match="decode-only"):
            TwineCodec().encode(
                bundle=None,
                runtime_data={},
                story_key=None,
                codec_state=None,
            )
