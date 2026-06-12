"""Contract tests for the blessed ``tangl.journal.compose`` stanzas.

Organized as one test class per helper: ``TestReplaceFirst``,
``TestAssembleSlots``, and ``TestBeatOverlay``.
"""

from __future__ import annotations

import pytest

from tangl.journal.compose import REST_SLOT, assemble_slots, beat_overlay, replace_first
from tangl.journal.fragments import ChoiceFragment, ContentFragment, GroupFragment

# ============================================================================
# Helpers
# ============================================================================


def _content(text: str, **kwargs) -> ContentFragment:
    return ContentFragment(content=text, **kwargs)


# ============================================================================
# Test classes
# ============================================================================


class TestReplaceFirst:
    def test_replaces_only_first_match(self) -> None:
        a, b, c = _content("a"), _content("b"), _content("c")
        replacement = _content("swap")

        result = replace_first([a, b, c], lambda f: f.content in {"b", "c"}, replacement)

        assert [f.content for f in result] == ["a", "swap", "c"]

    def test_no_match_returns_equal_batch(self) -> None:
        a, b = _content("a"), _content("b")

        result = replace_first([a, b], lambda f: False, _content("swap"))

        assert result == [a, b]

    def test_insert_missing_prepends_replacement(self) -> None:
        a = _content("a")
        replacement = _content("swap")

        result = replace_first([a], lambda f: False, replacement, insert_missing=True)

        assert [f.content for f in result] == ["swap", "a"]


class TestAssembleSlots:
    def test_orders_fragments_by_slot(self) -> None:
        setting = _content("setting")
        incident = _content("incident", tags={"incident"})
        fragments = [incident, setting]

        result = assemble_slots(
            fragments,
            order=("setting", "incident"),
            classify=lambda f: "incident" if "incident" in (f.tags or set()) else "setting",
        )

        assert [f.content for f in result] == ["setting", "incident"]

    def test_rest_slot_collects_unclassified_at_marker(self) -> None:
        setting = _content("setting")
        choice = ChoiceFragment(text="go")

        result = assemble_slots(
            [choice, setting],
            order=(REST_SLOT, "setting"),
            classify=lambda f: "setting" if isinstance(f, ContentFragment) else None,
        )

        assert result == [choice, setting]

    def test_rest_appends_at_end_when_marker_omitted(self) -> None:
        setting = _content("setting")
        choice = ChoiceFragment(text="go")

        result = assemble_slots(
            [choice, setting],
            order=("setting",),
            classify=lambda f: "setting" if isinstance(f, ContentFragment) else None,
        )

        assert result == [setting, choice]

    def test_duplicate_slot_names_raise(self) -> None:
        with pytest.raises(ValueError, match="unique"):
            assemble_slots([], order=("setting", "setting"), classify=lambda f: None)

    def test_relative_order_within_slot_is_stable(self) -> None:
        first, second = _content("first"), _content("second")

        result = assemble_slots(
            [first, second],
            order=("setting",),
            classify=lambda f: "setting",
        )

        assert [f.content for f in result] == ["first", "second"]


class TestBeatOverlay:
    def test_overlay_binds_member_uids(self) -> None:
        members = [_content("a"), _content("b")]

        overlay = beat_overlay(members, beat="arrival")

        assert isinstance(overlay, GroupFragment)
        assert overlay.group_type == "beat"
        assert overlay.content == "arrival"
        assert overlay.member_ids == [f.uid for f in members]

    def test_extra_metadata_travels_on_overlay(self) -> None:
        overlay = beat_overlay([], beat="arrival", segment_kind="scene")

        assert overlay.segment_kind == "scene"
