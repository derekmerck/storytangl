
from tangl33.core import Tier, TieredMap
from tangl33.core.tiered_map import _sanitise


def test_inject_and_order():
    tm = TieredMap()
    tm.inject(Tier.DOMAIN,  {"x": 1})

    # NODE layer stays at index of Tier.NODE and remains empty
    assert list(tm.maps)[tm._tier_index.index(Tier.NODE)] == {}

    # DOMAIN layer contains our value
    assert list(tm.maps)[tm._tier_index.index(Tier.DOMAIN)] == {"x": 1}
    assert tm['x'] == 1

    tm.inject(Tier.NODE,    {"y": 2})
    assert list(tm.maps)[tm._tier_index.index(Tier.NODE)] == {"y": 2}
    assert list(tm.maps)[tm._tier_index.index(Tier.DOMAIN)] == {"x": 1}      # DOMAIN last
    assert tm['x'] == 1
    assert tm['y'] == 2

    # shadow domain
    tm.inject(Tier.GRAPH, {"x": 3})
    assert tm['x'] == 3
    assert tm['y'] == 2

def test_sanitise():
    assert _sanitise("little-dog") == "little_dog"
    assert _sanitise("scene1/village/elder") == "scene1_village_elder"
    assert _sanitise("123bad") == "_123bad"

def test_sanitised_keys():
    tm = TieredMap()
    tm.inject(Tier.NODE, {"little-dog": 1, "123bad": 2})
    assert "little_dog" in tm
    assert "_123bad" in tm


