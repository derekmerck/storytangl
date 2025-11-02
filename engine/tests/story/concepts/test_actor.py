from types import SimpleNamespace

import pytest

from tangl.core import Graph
from tangl.story.concepts.actor import Actor, Role
from tangl.vm.provision.provisioner import Provisioner, ProvisioningPolicy

@pytest.fixture
def actor_role():
    g = Graph()
    actor = Actor(label="bob", graph=g)
    role = Role(actor_ref="bob", graph=g)
    yield actor, role

def test_actor_role_sat(actor_role) -> None:
    actor, role = actor_role
    print(role.get_selection_criteria())
    assert role.satisfied_by(actor)

def test_role_prov(actor_role):
    actor, role = actor_role
    ctx = SimpleNamespace(graph=actor.graph)
    prov = Provisioner()
    offers = prov.get_offers(role.requirement, ctx=ctx)

    assert len(offers) == 1
    assert offers[0].operation == ProvisioningPolicy.EXISTING

    for offer in offers:
        print(offer.describe())

    res = offers[0].accept(ctx=ctx)
    print(f"accepted: {res}")
    role.requirement.provider = res
    assert role.satisfied

    assert role in actor.roles

def test_actor_role_unsat(actor_role):
    actor, role = actor_role
    wants_alice = Role(actor_ref="alice", actor_template={"label": "alice"}, graph=actor.graph)
    assert not wants_alice.satisfied_by(actor)

def test_alice_templ_prov(actor_role):
    actor, role = actor_role
    prov = Provisioner()
    wants_alice = Role(actor_ref="alice", actor_template={"label": "alice"}, graph=actor.graph)
    ctx = SimpleNamespace(graph=actor.graph)
    offers = prov.get_offers(wants_alice.requirement, ctx=ctx)

    assert len(offers) == 1
    assert offers[0].operation == ProvisioningPolicy.CREATE

    for offer in offers:
        print(offer.describe())

    res = offers[0].accept(ctx=ctx)
    print(f"accepted: {res}")
    wants_alice.requirement.provider = res
    assert wants_alice.satisfied

    assert wants_alice in res.roles

    wants_alice2 = Role(actor_ref="alice", actor_template={"label": "alice"}, graph=actor.graph)

    offers = prov.get_offers(wants_alice2.requirement, ctx=ctx)
    assert len(offers) >= 2  # find create; update is included, even though update is irrelevant
    for offer in offers:
        print(offer.describe())

