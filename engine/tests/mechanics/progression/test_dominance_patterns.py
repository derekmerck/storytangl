from __future__ import annotations

from tangl.mechanics.progression.dominance import CircularDominance


def test_circular_dominance_basic_rps():
    items = ["rock", "paper", "scissors"]
    pattern = {1: 1.0}

    matrix = CircularDominance.generate(items, pattern)

    for item in items:
        assert matrix[item][item] == 0.0

    for attacker in items:
        for defender in items:
            if attacker == defender:
                continue
            assert matrix[attacker][defender] == -matrix[defender][attacker]

    assert matrix["rock"]["paper"] == 1.0
    assert matrix["paper"]["scissors"] == 1.0
    assert matrix["scissors"]["rock"] == 1.0


def test_circular_dominance_pattern_skips_and_ignores_invalid_offsets():
    items = ["A", "B", "C", "D"]
    pattern = {1: 1.0, 2: 0.5, 4: 2.0, 0: 99.0}

    matrix = CircularDominance.generate(items, pattern)

    assert matrix["A"]["B"] == 1.0
    assert matrix["B"]["A"] == -1.0

    assert matrix["A"]["C"] == 0.5
    assert matrix["C"]["A"] == -0.5

    for name in items:
        assert matrix[name][name] == 0.0
