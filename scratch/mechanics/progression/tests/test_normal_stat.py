from __future__ import annotations

from tangl.mechanics.progression.stats import NormalStat as Stat, NormalStatHandler
from tangl.mechanics.progression.measures import Quality

def test_inequalities():
    assert Stat(16.0) == Quality.HIGH
    assert Stat(Quality.HIGH) == Quality.HIGH
    assert Stat("high") == Quality.HIGH

    assert Stat("low") < Quality.HIGH
    assert Stat(10.0) < Stat(20.0)
    print(Stat(10.0))
    assert Stat(10.0) > 1  # avg > low


def test_probabities():

    quals = [Quality(x) for x in range(1, 6)]

    # Same val (relatively the same, P success ~0.5)
    for pair in zip(quals, quals):
        print( pair, NormalStatHandler.relative_likelihood(pair[0], pair[1]) )
        assert 0.45 < NormalStatHandler.relative_likelihood(pair[0], pair[1]) < 0.55

    # One easier (relatively easier, P success ~0.75)
    for pair in zip(quals, quals[1:]):
        print( pair, NormalStatHandler.relative_likelihood(pair[0], pair[1]) )
        assert 0.65 < NormalStatHandler.relative_likelihood(pair[0], pair[1]) < 0.9

    # One harder (relatively harder, P success ~0.2)
    for pair in zip(quals[1:], quals):
        print( pair, NormalStatHandler.relative_likelihood(pair[0], pair[1]) )
        assert 0.1 < NormalStatHandler.relative_likelihood(pair[0], pair[1]) < 0.35

    # Two easier (relatively much easier, P success ~0.9)
    for pair in zip(quals, quals[2:]):
        print( pair, NormalStatHandler.relative_likelihood(pair[0], pair[1]) )
        assert 0.9 < NormalStatHandler.relative_likelihood(pair[0], pair[1]) < 1.0

    # Two harder (relatively much harder, P failure ~0.1)
    for pair in zip(quals[2:], quals):
        print( pair, NormalStatHandler.relative_likelihood(pair[0], pair[1]) )
        assert 0.0 < NormalStatHandler.relative_likelihood(pair[0], pair[1]) < 0.1

expected_results = """
(<VERY_LOW>, <VERY_LOW>) 0.5
(<LOW>, <LOW>) 0.5
(<AVERAGE>, <AVERAGE>) 0.5
(<HIGH>, <HIGH>) 0.5
(<VERY_HIGH>, <VERY_HIGH>) 0.5
(<VERY_LOW>, <LOW>) 0.691462461274013
(<LOW>, <AVERAGE>) 0.8413447460685429
(<AVERAGE>, <HIGH>) 0.8783274954256187
(<HIGH>, <VERY_HIGH>) 0.691462461274013
(<LOW>, <VERY_LOW>) 0.30853753872598694
(<AVERAGE>, <LOW>) 0.15865525393145707
(<HIGH>, <AVERAGE>) 0.12167250457438128
(<VERY_HIGH>, <HIGH>) 0.30853753872598694
(<VERY_LOW>, <AVERAGE>) 0.9331927987311419
(<LOW>, <HIGH>) 0.9848698599897642
(<AVERAGE>, <VERY_HIGH>) 0.9522096477271853
(<AVERAGE>, <VERY_LOW>) 0.06680720126885809
(<HIGH>, <LOW>) 0.015130140010235826
(<VERY_HIGH>, <AVERAGE>) 0.04779035227281475
"""
