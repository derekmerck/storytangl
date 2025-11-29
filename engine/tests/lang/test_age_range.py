from tangl.lang.age_range import AgeRange
from tangl.core import Entity

def test_age_range_from_age_basic_bucketing():
    """
    AgeRange.from_age should bucket based on the IntEnum ordering / thresholds.
    With the current values (1..5), we effectively get an ordinal mapping.
    """
    assert AgeRange.from_age(-1) is AgeRange.OTHER
    assert AgeRange.from_age(0) is AgeRange.OTHER

    # Threshold-style behavior with monotonically increasing values
    assert AgeRange.from_age(1) is AgeRange.VERY_YOUNG
    assert AgeRange.from_age(2) is AgeRange.YOUNG
    assert AgeRange.from_age(3) is AgeRange.MID
    assert AgeRange.from_age(4) is AgeRange.OLD
    assert AgeRange.from_age(5) is AgeRange.VERY_OLD

    # Values above the highest threshold stay in the top bucket
    assert AgeRange.from_age(99) is AgeRange.VERY_OLD


def test_age_range_from_tags_numeric_only_uses_bucketed_age():
    """
    When only numeric age tags are present, AgeRange.from_tags should bucket
    using the highest age value.
    """
    e = Entity(tags={"age:1", "age:3", "age:2"})

    result = AgeRange.from_tags(e)

    assert result is AgeRange.MID


def test_age_range_from_tags_categorical_and_numeric_prefers_categorical_range():
    """
    If both categorical and numeric age tags are present, the categorical tags
    win, and we pick the 'oldest' of those ranges.
    """
    e = Entity(
        tags={
            "age:child",      # maps to VERY_YOUNG/CHILD via EnumPlus
            "age:100",        # would bucket to VERY_OLD if numeric-only
        }
    )

    result = AgeRange.from_tags(e)

    # Because there is a categorical tag, we ignore numeric tags and use
    # the categorical range; with CHILD aliased to VERY_YOUNG, we expect that.
    assert result is AgeRange.VERY_YOUNG


def test_age_range_from_tags_no_relevant_tags_returns_other():
    """
    If there are no age-related tags at all, we fall back to OTHER.
    """
    e = Entity(tags={"foo:bar", "other:thing"})

    result = AgeRange.from_tags(e)

    assert result is AgeRange.OTHER