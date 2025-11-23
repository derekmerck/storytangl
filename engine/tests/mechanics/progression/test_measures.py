from __future__ import annotations

from tangl.mechanics.progression.measures import Quality


def test_quality_values_and_aliases():
    assert Quality.VERY_POOR == 1
    assert Quality.POOR == 2
    assert Quality.MID == 3
    assert Quality.HIGH == 4
    assert Quality.VERY_HIGH == 5

    # Aliases
    assert Quality.OK is Quality.MID
    assert Quality.GOOD is Quality.HIGH
    assert Quality.VERY_GOOD is Quality.VERY_HIGH


def test_quality_from_name():
    assert Quality.from_name("mid") is Quality.MID
    assert Quality.from_name("GOOD") is Quality.GOOD
    assert Quality.from_name("very_good") is Quality.VERY_GOOD
    assert Quality.from_name(" Average ") is Quality.MID
