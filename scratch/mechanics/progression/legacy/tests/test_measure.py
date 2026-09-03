import types

from tangl.mechanics.progression.measures import *


def test_measure_ns():

    assert eval("Q.GOOD", {"Q": measure_namespace}) is Result.GOOD
    assert eval("Q.GOOD", {"Q": measure_namespace}) == 4

    assert eval("Q.LARGE", {"Q": measure_namespace}) is Size.LARGE
    assert eval("Q.LARGE", {"Q": measure_namespace}) == 4

    assert eval("Q.LARGE > Q.MID", {"Q": measure_namespace})

    assert eval("Q.NONE < Q.MID", {"Q": measure_namespace})
