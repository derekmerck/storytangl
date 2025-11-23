from __future__ import annotations

from mechanics.progression.measures import Quality
from mechanics.progression.stats.stat import Stat
from mechanics.progression.handlers.linear import LinearStatHandler


def test_stat_construct_from_fv_int_quality_str():
    s_fv = Stat(12.0)
    s_qv = Stat(4)
    s_quality = Stat(Quality.HIGH)
    s_str = Stat("mid")

    assert isinstance(s_fv.fv, float)
    assert 1 <= s_fv.qv <= 5

    assert s_qv.qv == 4
    assert s_quality.qv == Quality.HIGH.value
    assert s_str.quality is Quality.MID


def test_stat_equality_by_tier():
    a = Stat(10.0)
    b = Stat("mid")
    c = Stat(3)
    d = Stat(Quality.MID)

    assert a == b == c == d
    assert a == 3
    assert a == "mid"
    assert not (a == "good")  # different tier


def test_stat_ordering_by_fv():
    low = Stat(6.0)
    high = Stat(16.0)
    assert low < high
    assert not (high < low)


def test_stat_arithmetic_preserves_handler_and_is_reasonable():
    a = Stat(10.0)
    b = Stat(2.0)

    c = a + b
    d = a - b

    assert isinstance(c, Stat)
    assert isinstance(d, Stat)
    assert abs(c.fv - 12.0) < 1e-6
    assert abs(d.fv - 8.0) < 1e-6


def test_stat_delta():
    a = Stat(14.0)
    b = Stat(10.0)
    assert abs(a.delta(b) - 4.0) < 1e-6


def test_stat_with_handler_switch():
    s = Stat(10.0)
    s_lin = s.with_handler(LinearStatHandler)

    # fv preserved
    assert abs(float(s_lin) - float(s)) < 1e-6

    # Tier may change because mapping differs
    assert s_lin.handler is LinearStatHandler
