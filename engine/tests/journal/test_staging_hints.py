"""Staging axis vocabulary: viewer-relative naming, aliases, and refusals."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tangl.journal.fragments import StagingHints


@pytest.mark.parametrize(
    ("given", "expected"),
    [("left", "left"), ("right", "right"), ("mid", "mid"),
     ("screen_left", "left"), ("screen_right", "right"),
     ("center", "mid"), ("centre", "mid"), ("middle", "mid")],
)
def test_horizontal_aliases_normalize(given: str, expected: str) -> None:
    assert StagingHints(media_x=given).media_x == expected


@pytest.mark.parametrize("rejected", ["stage_left", "stage_right"])
def test_theatrical_names_are_refused_rather_than_guessed(rejected: str) -> None:
    """Stage left is the performer's left, so it inverts a viewer-named grid."""

    with pytest.raises(ValidationError, match="not a staging position"):
        StagingHints(media_x=rejected)


def test_vertical_levels_and_flip_are_independent_fields() -> None:
    hints = StagingHints(media_x="right", media_y="bottom", media_flip_h=True)

    assert (hints.media_x, hints.media_y, hints.media_flip_h) == ("right", "bottom", True)


def test_unset_axes_stay_none_for_ports_to_default() -> None:
    hints = StagingHints(media_flip_h=True)

    assert hints.media_x is None and hints.media_y is None
