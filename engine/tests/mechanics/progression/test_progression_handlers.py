from __future__ import annotations

import math

from tangl.mechanics.progression.handlers.probit import ProbitStatHandler
from tangl.mechanics.progression.handlers.linear import LinearStatHandler
from tangl.mechanics.progression.handlers.logint import LogIntStatHandler


def test_probit_fv_qv_roundtrip_basic():
    # Chosen so they land solidly in buckets
    for qv in range(1, 6):
        fv = ProbitStatHandler.fv_from_qv(qv)
        assert 1 <= ProbitStatHandler.qv_from_fv(fv) <= 5
        # Should land on the same tier
        assert ProbitStatHandler.qv_from_fv(fv) == qv


def test_probit_likelihood_monotone_in_delta():
    # For increasing delta, likelihood must be non-decreasing
    last = 0.0
    for delta in range(-15, 16):  # -15..15
        p = ProbitStatHandler.likelihood(delta)
        assert 0.0 <= p <= 1.0
        assert p >= last - 1e-9
        last = p

    # Check symmetry around 0
    center = ProbitStatHandler.likelihood(0.0)
    assert abs(center - 0.5) < 0.05


def test_linear_handler_monotone_and_clamped():
    last = 0.0
    for delta in range(-20, 21):
        p = LinearStatHandler.likelihood(delta)
        assert 0.0 <= p <= 1.0
        assert p >= last - 1e-9
        last = p


def test_logint_handler_reasonable_sigmoid():
    # Roughly sigmoid-shaped around 0
    low = LogIntStatHandler.likelihood(-10)
    mid = LogIntStatHandler.likelihood(0)
    high = LogIntStatHandler.likelihood(10)

    assert 0.0 <= low < mid < high <= 1.0
    assert mid == max(low, mid, high) or mid > low and mid < high
    assert mid == LogIntStatHandler.likelihood(0)
    assert abs(mid - 0.5) < 0.2
