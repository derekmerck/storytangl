import pytest
from tangl.mechanics.progression.stats.base_stat import Stat, StatHandler
from tangl.mechanics.progression.measures import Quality
from tangl.mechanics.progression.stat_domain_map import HasStats, PsychosomaticDomains

# Testing the Stat class


def test_initialization():
    m = Stat("mid")
    assert m.fv == 10.0, f"fv is {m.fv}"
    assert m.exp2 == 1.0, f"ev is {m.exp2}"
    assert m.qv == Quality.MID, f"qv is {m.qv}"

    m = Stat(10.0)
    assert m.fv == 10.0, f"fv is {m.fv}"
    assert m.exp2 == 1.0, f"ev is {m.exp2}"
    assert m.qv == Quality.MID, f"qv is {m.qv}"

    m = Stat(10.5)
    assert m.fv == 10.5, f"fv is {m.fv}"
    assert m.qv == Quality.MID, f"qv is {m.qv}"

    with pytest.raises(TypeError):
        m = Stat([])  # pass a type that's not allowed

    with pytest.raises(ValueError):
        m = Stat("invalid level")  # pass an invalid level string


def test_stat_quantized_value():
    stat = Stat(15.)
    assert stat.qv == Quality.HIGH

def test_stat_comparison():
    stat1 = Stat(10.)
    stat2 = Stat(15.)
    assert stat1 < stat2

    m1 = Stat("mid")
    m2 = Stat("small")

    assert m1 > m2
    assert m1 >= m2
    assert m2 < m1
    assert m2 <= m1
    assert m1 == Stat("mid")
    assert m1 != m2

def test_stat_arithmetic_operations():
    stat1 = Stat(10.)
    stat2 = Stat(5.)
    result = stat1 + stat2
    assert result.fv == 15.
    assert result.qv == Quality.HIGH

    result = stat1 - stat2
    assert result.fv == 5
    assert result.qv == Quality.LOW
#
# def test_stat_exp2_operations():
#     m1 = Stat("mid")
#     m2 = Stat("small")
#     m3 = m1 + m2
#     assert m3.exp2 == 1.5
#     assert m3.qv == Quality.MID
#
#     m3 = m1 - m2
#     assert m3.exp2 == 0.75       # one minus 1/2 a 1/2
#     assert m3.qv == Quality.LOW  # 0.75 goes to small, although it's equidistant
#
#     m3 = m1 * m2
#     assert m3.exp2 == 1 * 2**-1 * 2**-2
#     assert m3.qv == Quality.NONE
#
# def test_qual():
#     assert (Qu(1.0).q is Q.MAX)
#     assert (Qu(1.1).q is Q.MAX)
#     assert ((Qu(0.5) + Qu(0.2)).q is Q.HIGH)
#     assert ((Qu(0.5) - Qu(0.2)).q is Q.LOW)
#     assert ((Qu(0.5) * 2).q is Q.MAX)
#     assert ((Qu(0.5) / Qu(0.1)).q is Q.MAX)
#
#     assert (Qu(0.5) == Q.MID)
#     assert (Qu(0.4) == Q.MID)
#     assert (Qu(0.4) < Qu(0.5))
#     assert (Qu(0.4) >= Qu(0.5))
#     assert (Qu(0.4) <= Qu(0.5))
#     assert (Qu(0.5) < Q.HIGH)
#     assert (Qu(1.0) >= Q.HIGH)



# Testing the StatHandler class

def test_qv_from_fv_conversion():
    qv = StatHandler.qv_from_fv(18)
    assert qv == Quality.VERY_HIGH

def test_fv_from_qv_conversion():
    fv = StatHandler.fv_from_qv(Quality.MID)
    assert fv == 10

def test_stat_delta():
    delta = StatHandler.delta(5., 15.)
    # 15-5 = 10, (10 + 20) / 2 = 15
    assert delta == 15.

def test_likelihood_calculation():
    likelihood = StatHandler.likelihood(10.)
    assert likelihood == 0.5

class Character(HasStats):
    stat_domains = PsychosomaticDomains

def test_has_stats_integration():
    char = Character()
    assert char.stats['body'].fv == 10.
    assert char.stats['mind'].qv == Quality.MID

    # Testing attribute access
    assert char.BODY.fv == 10.
    assert char.MIND.qv == Quality.MID

    # Testing attribute access
    assert char.body.fv == 10.
    assert char.mind.qv == Quality.MID

    char = Character(stats=[1., 17.])
    assert char.body.fv == 1.0
    assert char.mind.qv == Quality.VERY_HIGH

def test_has_stats_currencies():

    char = Character(stats=[1., 17.])
    assert char.body.fv == 1.0
    assert char.mind.qv == Quality.VERY_HIGH

    print( char.wallet )

    assert char.stamina == 1.
    assert char.wit == 17.

