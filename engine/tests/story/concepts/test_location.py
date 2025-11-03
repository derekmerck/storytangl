
from types import SimpleNamespace

import pytest

from tangl.core import Graph
from tangl.story.concepts.location import Location, Setting
from tangl.vm.provision import GraphProvisioner, TemplateProvisioner

@pytest.fixture
def location_setting():
    g = Graph()
    location = Location(label="castle", graph=g)
    setting = Setting(location_ref="castle", graph=g)
    yield location, setting

def test_location_setting_sat(location_setting) -> None:
    location, setting = location_setting
    print(setting.get_selection_criteria())
    assert setting.satisfied_by(location)

def test_setting_prov(location_setting):
    location, setting = location_setting
    ctx = SimpleNamespace(graph=location.graph)
    prov = GraphProvisioner(node_registry=location.graph, layer="local")
    offers = list(prov.get_dependency_offers(setting.requirement, ctx=ctx))

    assert len(offers) == 1
    assert offers[0].operation == "EXISTING"

    res = offers[0].accept(ctx=ctx)
    print(f"accepted: {res}")
    setting.requirement.provider = res
    assert setting.satisfied

    assert setting in location.settings

def test_location_setting_unsat(location_setting):
    location, setting = location_setting
    wants_city = Setting(location_ref="city", location_template={"label": "city"}, graph=location.graph)
    assert not wants_city.satisfied_by(location)

def test_alice_templ_prov(location_setting):
    location, setting = location_setting
    graph_prov = GraphProvisioner(node_registry=location.graph, layer="local")
    template_prov = TemplateProvisioner(layer="author")
    wants_city = Setting(location_ref="city", location_template={"label": "city"}, graph=location.graph)
    ctx = SimpleNamespace(graph=location.graph)
    offers = list(template_prov.get_dependency_offers(wants_city.requirement, ctx=ctx))

    assert len(offers) == 1
    assert offers[0].operation == "CREATE"

    res = offers[0].accept(ctx=ctx)
    print(f"accepted: {res}")
    wants_city.requirement.provider = res
    assert wants_city.satisfied

    assert wants_city in res.settings

    wants_city2 = Setting(location_ref="city", location_template={"label": "city"}, graph=location.graph)

    offers = []
    offers.extend(graph_prov.get_dependency_offers(wants_city2.requirement, ctx=ctx))
    offers.extend(template_prov.get_dependency_offers(wants_city2.requirement, ctx=ctx))
    kinds = {offer.operation for offer in offers}
    assert "EXISTING" in kinds
    assert "CREATE" in kinds

