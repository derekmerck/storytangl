from __future__ import annotations

from tangl.mechanics.progression.outcomes import Outcome, sample_outcome


def test_sample_outcome_bounds_and_types():
    # Trivial boundary checks
    for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
        o = sample_outcome(p, roll=0.5)
        assert isinstance(o, Outcome)


def test_sample_outcome_monotone_in_p_for_fixed_roll():
    """
    For any fixed roll, increasing p_success should not
    produce “worse” outcomes (in terms of enum value).
    """
    for roll in [0.1, 0.3, 0.5, 0.7, 0.9]:
        last = Outcome.DISASTER
        for p in [0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]:
            o = sample_outcome(p, roll=roll)
            assert o.value >= last.value
            last = o
