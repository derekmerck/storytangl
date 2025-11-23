from __future__ import annotations

from tangl.mechanics.progression.presets.registry import all_presets, get_preset
from tangl.mechanics.progression.presets import cyberpunk, fantasy  # noqa: F401


def test_fantasy_presets_registered_and_shape():
    presets = all_presets()
    assert "fantasy3" in presets
    assert "fantasy5" in presets

    fantasy3 = get_preset("fantasy3")
    assert fantasy3.complexity == 3
    assert len(fantasy3.stats) == 3
    assert not fantasy3.dominance_matrix

    fantasy5 = get_preset("fantasy5")
    assert fantasy5.complexity == 5
    assert len(fantasy5.stats) == 5

    names = fantasy5.stat_names
    matrix = fantasy5.dominance_matrix
    assert set(matrix.keys()) == set(names)
    for row in matrix.values():
        assert set(row.keys()) == set(names)


def test_cyberpunk_preset_registered_and_theme():
    presets = all_presets()
    assert "cyberpunk5" in presets

    cp5 = get_preset("cyberpunk5")
    assert cp5.theme == "cyberpunk"
    assert cp5.complexity == 5

    assert cp5.dominance_matrix
