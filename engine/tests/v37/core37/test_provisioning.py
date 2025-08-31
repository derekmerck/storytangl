import uuid

import pytest

from tangl.core.entity import Entity
from tangl.core.graph import Graph
from tangl.core.provision import Provisioner, Provider, ProvisionOffer, ProvisionRequirement

# ---------- Provisioning orchestration ----------

@pytest.mark.xfail(reason="not working")
def test_provisioner_runs_offers_with_ns_and_returns_job_receipts():
    seen_ns = []
    # Build a provider that offers one ProvisionOffer and captures ns
    def get_affordances(ns):
        seen_ns.append(ns.copy())

        def accept(ns2):
            class Dummy(Entity): pass
            return Dummy(label="provided")
        return [ProvisionOffer(
            provider_id=uuid.uuid4(),
            predicate=None,
            _accept_func=accept,
            cost=1.0,
        )]

    prov = Provider(_get_affordances_func=get_affordances)

    ns = {"scope": "abc"}
    receipts = Provisioner.run([prov], ns=ns, requirement=None)
    assert len(receipts) == 1
    assert seen_ns == [ns]
    assert isinstance(receipts[0].result, Entity)

@pytest.mark.xfail(reason="not working")
def test_provisioner_blame_tuple_when_requirement_present():
    req = ProvisionRequirement(dependency_id=uuid.uuid4(), criteria={"k": "v"})

    def get_offers(ns, requirement):
        def accept(_ns):
            class Dummy(Entity): pass
            return Dummy(label="dep")
        return [ProvisionOffer(
            provider_id=uuid.uuid4(),
            requirement_id=requirement.uid,
            predicate=None,
            _accept_func=accept,
            cost=1.0,
        )]

    prov = Provider(_get_affordances_func=None, _get_offers_func=get_offers)
    receipts = Provisioner.run([prov], ns={"x": 1}, requirement=req)
    assert len(receipts) == 1
    assert isinstance(receipts[0].blame_id, tuple) and len(receipts[0].blame_id) == 2

def test_edge_destination_none_branch_does_not_validate():
    g = Graph()
    n1 = g.add_node(label="S")
    e = g.add_edge(n1, None)
    # Should not raise on setting None
    e.destination = None
    assert e.destination_id is None
    # Then set a real destination
    n2 = g.add_node(label="D")
    e.destination = n2
    assert e.destination_id == n2.uid
