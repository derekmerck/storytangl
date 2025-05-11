from tangl33.core import Tier, TierView, Service
from tangl33.core.tier_view import _sanitise


def test_inject_and_order():
    tm = TierView()
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
    tm = TierView()
    tm.inject(Tier.NODE, {"little-dog": 1, "123bad": 2})
    assert "little_dog" in tm
    assert "_123bad" in tm


def test_compose_precedence_and_shadowing():
    # make three simple layers for the PROVIDER service
    node_layer   = {"x": "node"}
    graph_layer  = {"x": "graph", "g": "graph"}
    domain_layer = {"d": "domain"}

    view = TierView.compose(
        service=Service.PROVIDER,
        NODE=node_layer,
        GRAPH=graph_layer,
        DOMAIN=domain_layer,
    )

    # ChainMap should respect inner→outer order
    # 'x' is shadowed by node layer, 'g' comes from graph, 'd' from domain
    assert view["x"] == "node"
    assert view["g"] == "graph"
    assert view["d"] == "domain"

    # Mutating the underlying layer is reflected in the view
    node_layer["x"] = "node-mut"
    assert view["x"] == "node-mut"

    view._get_layer("node")["x"] = "node-mut2"
    assert view["node", "x"] == "node-mut2"
    assert view["x"] == "node-mut2"
    assert node_layer["x"] == "node-mut2"

    view["node", "x"] = "node-mut3"
    assert view["node", "x"] == "node-mut3"
    assert view["x"] == "node-mut3"
    assert node_layer["x"] == "node-mut3"
