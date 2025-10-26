
from tangl.mechanics.progression.stats import ExpStat
from tangl.mechanics.progression.measures import Quality


def test_exp_stat():
    print( ExpStat(20.0) )
    assert ExpStat(20.0) == 5
    assert ExpStat(20.0) == Quality.VERY_HIGH
    assert ExpStat(5) == Quality.VERY_HIGH

    assert ExpStat(3) == Quality.MID

    print( ExpStat(3).fv, ExpStat(4).fv )
    print( (ExpStat(3) + ExpStat(3)).ev )
    print( (ExpStat(3) + ExpStat(3)).qv )

    assert ExpStat('mid') + ExpStat('mid') == Quality.HIGH
    assert ExpStat('high') + ExpStat('high') == Quality.VERY_HIGH
    assert ExpStat('high') + ExpStat('mid') + ExpStat('mid') == Quality.VERY_HIGH

    print( (ExpStat(4) + ExpStat(4)).qv )

    for i in range(1, 6):
        print( i, ExpStat(i), ExpStat(i).exp2 )

def test_exp_stat_arithmetic_operations():
    m1 = ExpStat("mid")
    print( m1.ev, m1.qv )
    assert 2.9 < m1.ev < 3.1
    m2 = ExpStat("small")
    print( m2.ev, m2.qv )
    assert 1.9 < m2.ev < 2.1
    m3 = m1 + m2
    print( m3.ev, m3.qv )
    assert 3.4 < m3.ev < 3.6
    assert m3.qv == Quality.MID

    m3 = m1 - m2
    assert 0.5 < m3.exp2 < 0.6   # one minus 1/2 a 1/2
    assert m3.qv == Quality.LOW  # 0.75 goes to small, although it's equidistant

    # m3 = m1 * m2
    # assert m3.exp2 == 1 * 2**-1 * 2**-2
    # assert m3.qv == Quality.NONE

