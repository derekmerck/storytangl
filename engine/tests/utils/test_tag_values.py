"""Tests for ``tangl.utils.tag_values``."""

from __future__ import annotations

from enum import StrEnum

import pytest

from tangl.utils.tag_values import get_tag_values


class Mood(StrEnum):
    CALM = "calm"
    ALERT = "alert"


class TestGetTagValues:
    def test_extracts_prefixed_string_values(self) -> None:
        tags = {"age:adult", "age:teen", "role:guard"}

        values = get_tag_values(tags, prefix="age")

        assert values == {"adult", "teen"}

    def test_coerces_prefixed_int_values(self) -> None:
        tags = {"age:12", "age:40", "role:guard"}

        values = get_tag_values(tags, prefix="age", value_type=int)

        assert values == {12, 40}

    def test_coerces_prefixed_enum_values(self) -> None:
        tags = {"mood:calm", "mood:alert", "role:guard"}

        values = get_tag_values(tags, prefix="mood", value_type=Mood)

        assert values == {Mood.CALM, Mood.ALERT}

    def test_accepts_direct_enum_members_without_prefix(self) -> None:
        tags = {Mood.CALM, Mood.ALERT}

        values = get_tag_values(tags, value_type=Mood)

        assert values == {Mood.CALM, Mood.ALERT}

    def test_rejects_missing_prefix_for_scalar_string_or_int_types(self) -> None:
        with pytest.raises(TypeError, match="prefix is required"):
            get_tag_values({"12"}, value_type=int)

        with pytest.raises(TypeError, match="prefix is required"):
            get_tag_values({"guard"}, value_type=str)

    def test_requires_some_parse_mode(self) -> None:
        with pytest.raises(TypeError, match="Expected at least one"):
            get_tag_values({"guard"})
