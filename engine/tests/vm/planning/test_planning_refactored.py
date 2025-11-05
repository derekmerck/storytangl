"""
Unit tests for refactored planning phase (v3.7).

Tests cover:
- Deduplication of EXISTING offers by provider_id
- Selection of best offers by (cost, proximity, registration order)
- Full planning pipeline integration
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from tangl.core import Graph, Node
from tangl.vm import Frame, ResolutionPhase as P, Context
from tangl.vm.provision import (
    DependencyOffer,
    AffordanceOffer,
    ProvisionCost,
    Requirement,
    Dependency,
    GraphProvisioner,
    TemplateProvisioner,
    ProvisioningPolicy,
    PlanningReceipt,
)

from tangl.vm.dispatch.planning_v372 import _deduplicate_offers, _select_best_offer, _policy_from_offer


# =============================================================================
# Unit Tests for Helper Functions
# =============================================================================

def test_deduplicate_offers_keeps_cheapest_existing():
    """Deduplication keeps the cheapest EXISTING offer for the same provider."""
    door_id = uuid4()
    req_id = uuid4()
    
    # Create two EXISTING offers for the same door
    expensive_offer = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=door_id,
        cost=ProvisionCost.DIRECT,
        proximity=999,  # Distant
        accept_func=lambda ctx: None,
    )
    
    cheap_offer = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=door_id,
        cost=ProvisionCost.DIRECT,
        proximity=0,  # Close
        accept_func=lambda ctx: None,
    )
    
    offers = [expensive_offer, cheap_offer]
    deduplicated = _deduplicate_offers(offers)
    
    assert len(deduplicated) == 1
    assert deduplicated[0] is cheap_offer
    assert deduplicated[0].proximity == 0


def test_deduplicate_offers_preserves_non_existing():
    """Deduplication preserves CREATE/UPDATE/CLONE offers."""
    door_id = uuid4()
    req_id = uuid4()
    
    existing_offer = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=door_id,
        cost=ProvisionCost.DIRECT,
        accept_func=lambda ctx: None,
    )
    
    create_offer = DependencyOffer(
        requirement_id=req_id,
        operation="CREATE",
        provider_id=None,  # CREATE offers don't have provider_id
        cost=ProvisionCost.CREATE,
        accept_func=lambda ctx: None,
    )
    
    offers = [existing_offer, create_offer]
    deduplicated = _deduplicate_offers(offers)
    
    assert len(deduplicated) == 2
    # Sorted by cost, so EXISTING comes first
    assert deduplicated[0] is existing_offer
    assert deduplicated[1] is create_offer


def test_deduplicate_offers_sorts_by_cost_proximity_order():
    """Deduplication sorts offers by (cost, proximity, registration order)."""
    door_id = uuid4()
    req_id = uuid4()
    
    # Three EXISTING offers for different doors
    offer1 = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        proximity=10,
        accept_func=lambda ctx: None,
    )
    
    offer2 = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        proximity=5,  # Closer
        accept_func=lambda ctx: None,
    )
    
    offer3 = DependencyOffer(
        requirement_id=req_id,
        operation="CREATE",
        provider_id=None,
        cost=ProvisionCost.CREATE,  # More expensive
        proximity=0,
        accept_func=lambda ctx: None,
    )
    
    offers = [offer1, offer2, offer3]
    deduplicated = _deduplicate_offers(offers)
    
    assert len(deduplicated) == 3
    assert deduplicated[0] is offer2  # DIRECT + closest
    assert deduplicated[1] is offer1  # DIRECT + farther
    assert deduplicated[2] is offer3  # CREATE


def test_deduplicate_offers_uses_registration_order_as_tiebreaker():
    """When cost and proximity are equal, registration order breaks ties."""
    door_id = uuid4()
    req_id = uuid4()
    
    offer1 = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        proximity=10,
        accept_func=lambda ctx: None,
    )
    
    offer2 = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        proximity=10,  # Same proximity
        accept_func=lambda ctx: None,
    )
    
    offers = [offer1, offer2]
    deduplicated = _deduplicate_offers(offers)
    
    assert len(deduplicated) == 2
    assert deduplicated[0] is offer1  # Registered first


def test_select_best_offer_chooses_cheapest():
    """Selection chooses the offer with lowest cost."""
    req_id = uuid4()
    
    expensive = DependencyOffer(
        requirement_id=req_id,
        operation="CREATE",
        cost=ProvisionCost.CREATE,
        accept_func=lambda ctx: None,
    )
    
    cheap = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        accept_func=lambda ctx: None,
    )
    
    offers = [expensive, cheap]
    best = _select_best_offer(offers)
    
    assert best is cheap


def test_select_best_offer_prefers_proximity():
    """When costs are equal, selection prefers closer proximity."""
    req_id = uuid4()
    
    distant = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        proximity=999,
        accept_func=lambda ctx: None,
    )
    
    close = DependencyOffer(
        requirement_id=req_id,
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        proximity=0,
        accept_func=lambda ctx: None,
    )
    
    offers = [distant, close]
    best = _select_best_offer(offers)
    
    assert best is close


def test_select_best_offer_returns_none_for_empty_list():
    """Selection returns None when no offers are available."""
    best = _select_best_offer([])
    assert best is None


def test_policy_from_offer():
    """Extract ProvisioningPolicy from offer operation string."""
    offer = DependencyOffer(
        requirement_id=uuid4(),
        operation="EXISTING",
        provider_id=uuid4(),
        cost=ProvisionCost.DIRECT,
        accept_func=lambda ctx: None,
    )
    
    policy = _policy_from_offer(offer)
    assert policy is ProvisioningPolicy.EXISTING


# =============================================================================
# Integration Tests with Full Planning Pipeline
# =============================================================================

def _make_context(graph: Graph) -> SimpleNamespace:
    """Create a minimal context for testing."""
    return SimpleNamespace(graph=graph, provision_offers={}, provision_builds=[])


def test_planning_prefers_existing_over_create():
    """Planning phase prefers EXISTING offers over CREATE when both available."""
    graph = Graph(label="demo")
    cursor = graph.add_node(label="scene")
    existing_door = graph.add_node(label="door")
    
    requirement = Requirement(
        graph=graph,
        identifier="door",
        template={"obj_cls": Node, "label": "door"},
        policy=ProvisioningPolicy.ANY,
    )
    Dependency(graph=graph, source=cursor, requirement=requirement, label="needs_door")
    
    frame = Frame(graph=graph, cursor_id=cursor.uid)
    
    # Register provisioners
    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        TemplateProvisioner(layer="author"),
    ]
    
    @frame.local_behaviors.register(task="get_provisioners", priority=0)
    def _supply_provisioners(*_, **__):
        return provisioners
    
    # Run planning phase
    receipt = frame.run_phase(P.PLANNING)
    
    assert isinstance(receipt, PlanningReceipt)
    assert requirement.provider is existing_door
    assert receipt.attached == 1
    assert receipt.created == 0


def test_planning_deduplicates_multiple_provisioners():
    """Multiple provisioners offering the same node are deduplicated."""
    graph = Graph(label="demo")
    cursor = graph.add_node(label="scene")
    door = graph.add_node(label="door")
    
    requirement = Requirement(
        graph=graph,
        identifier="door",
        policy=ProvisioningPolicy.EXISTING,
    )
    Dependency(graph=graph, source=cursor, requirement=requirement, label="needs_door")
    
    frame = Frame(graph=graph, cursor_id=cursor.uid)
    
    # Register TWO provisioners that will both offer the same door
    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        GraphProvisioner(node_registry=graph, layer="global"),
    ]
    
    @frame.local_behaviors.register(task="get_provisioners", priority=0)
    def _supply_provisioners(*_, **__):
        return provisioners
    
    # Run planning phase
    receipt = frame.run_phase(P.PLANNING)
    
    assert isinstance(receipt, PlanningReceipt)
    assert requirement.provider is door
    assert receipt.attached == 1
    # Only ONE build receipt should exist (deduplication worked)
    builds = []
    for call_receipt in frame.phase_receipts.get(P.PLANNING, []):
        if isinstance(call_receipt.result, list):
            builds.extend(call_receipt.result)
    dependency_builds = [b for b in builds if hasattr(b, 'requirement_id') and b.requirement_id == requirement.uid]
    assert len(dependency_builds) == 1


def test_planning_marks_unresolved_hard_requirement():
    """Hard requirements without offers are marked unresolved."""
    graph = Graph(label="demo")
    cursor = graph.add_node(label="scene")
    
    requirement = Requirement(
        graph=graph,
        identifier="missing",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=True,
    )
    Dependency(graph=graph, source=cursor, requirement=requirement, label="needs_missing")
    
    frame = Frame(graph=graph, cursor_id=cursor.uid)
    
    # Register provisioner (but it won't find "missing")
    provisioners = [GraphProvisioner(node_registry=graph, layer="local")]
    
    @frame.local_behaviors.register(task="get_provisioners", priority=0)
    def _supply_provisioners(*_, **__):
        return provisioners
    
    # Run planning phase
    receipt = frame.run_phase(P.PLANNING)
    
    assert isinstance(receipt, PlanningReceipt)
    assert requirement.provider is None
    assert requirement.is_unresolvable is True
    assert receipt.unresolved_hard_requirements == [requirement.uid]


def test_planning_waives_soft_requirement():
    """Soft requirements without offers are waived, not unresolved."""
    graph = Graph(label="demo")
    cursor = graph.add_node(label="scene")
    
    requirement = Requirement(
        graph=graph,
        identifier="missing",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=False,  # Soft
    )
    Dependency(graph=graph, source=cursor, requirement=requirement, label="needs_missing")
    
    frame = Frame(graph=graph, cursor_id=cursor.uid)
    
    # Register provisioner (but it won't find "missing")
    provisioners = [GraphProvisioner(node_registry=graph, layer="local")]
    
    @frame.local_behaviors.register(task="get_provisioners", priority=0)
    def _supply_provisioners(*_, **__):
        return provisioners
    
    # Run planning phase
    receipt = frame.run_phase(P.PLANNING)
    
    assert isinstance(receipt, PlanningReceipt)
    assert requirement.provider is None
    assert receipt.unresolved_hard_requirements == []
    assert receipt.waived_soft_requirements == [requirement.uid]


def test_planning_creates_when_no_existing():
    """Planning creates new nodes when EXISTING not found but CREATE available."""
    graph = Graph(label="demo")
    cursor = graph.add_node(label="scene")
    
    requirement = Requirement(
        graph=graph,
        identifier="new_thing",
        template={"obj_cls": Node, "label": "new_thing"},
        policy=ProvisioningPolicy.ANY,
    )
    Dependency(graph=graph, source=cursor, requirement=requirement, label="needs_new_thing")
    
    frame = Frame(graph=graph, cursor_id=cursor.uid)
    
    # Register provisioners (no EXISTING, but CREATE available)
    provisioners = [
        GraphProvisioner(node_registry=graph, layer="local"),
        TemplateProvisioner(layer="author"),
    ]
    
    @frame.local_behaviors.register(task="get_provisioners", priority=0)
    def _supply_provisioners(*_, **__):
        return provisioners
    
    # Run planning phase
    receipt = frame.run_phase(P.PLANNING)
    
    assert isinstance(receipt, PlanningReceipt)
    assert requirement.provider is not None
    assert requirement.provider.label == "new_thing"
    assert receipt.created == 1
    assert receipt.attached == 0

@pytest.mark.xfail(reason="Affordance api needs refactoring")
def test_planning_affordances_dont_duplicate_labels():
    """Affordances with the same label don't collide per destination."""
    graph = Graph(label="demo")
    cursor = graph.add_node(label="scene")
    companion1 = graph.add_node(label="companion1")
    companion2 = graph.add_node(label="companion2")
    
    frame = Frame(graph=graph, cursor_id=cursor.uid)
    
    # Create a custom provisioner that offers affordances
    from tangl.vm.provision import Provisioner, Affordance
    
    class TestAffordanceProvisioner(Provisioner):
        def get_affordance_offers(self, node, *, ctx):
            # Offer two affordances with the SAME label
            def make_affordance1(ctx, dest):
                # todo: need to pass in a requirement or infer the requirement from the params
                return Affordance(
                    graph=ctx.graph,
                    label="talk",
                    requirement={'provider_id': companion1.uid, 'graph': ctx.graph},
                    destination=dest,
                )
            
            def make_affordance2(ctx, dest):
                # todo: need to pass in a requirement or infer the requirement from the params
                return Affordance(
                    graph=ctx.graph,
                    label="talk",  # Same label!
                    requirement={'provider_id': companion2.uid, 'graph': ctx.graph},
                    destination=dest,
                )
            
            yield AffordanceOffer(
                label="talk",
                accept_func=make_affordance1,
                cost=ProvisionCost.DIRECT,
            )
            
            yield AffordanceOffer(
                label="talk",
                accept_func=make_affordance2,
                cost=ProvisionCost.DIRECT,
            )
    
    provisioners = [TestAffordanceProvisioner()]
    
    @frame.local_behaviors.register(task="get_provisioners", priority=0)
    def _supply_provisioners(*_, **__):
        return provisioners
    
    # Run planning phase
    receipt = frame.run_phase(P.PLANNING)
    
    # Only ONE affordance should be attached (label uniqueness enforced)
    assert isinstance(receipt, PlanningReceipt)
    # The receipt counts affordances in the "attached" counter
    # Since affordances are always EXISTING policy, they increment attached
    builds = []
    for call_receipt in frame.phase_receipts.get(P.PLANNING, []):
        if isinstance(call_receipt.result, list):
            builds.extend(call_receipt.result)
    affordance_builds = [b for b in builds if hasattr(b, 'requirement_id') and b.requirement_id.int == 0]
    assert len(affordance_builds) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
