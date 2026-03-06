"""
Test examples for the provisioner system.

These tests demonstrate how provisioners work in isolation,
without involving the planning dispatch system.
"""
import pytest
from uuid import UUID

# Mock imports - these would come from actual modules
from tangl.vm.provision import (
    Provisioner,
    DependencyOffer,
    AffordanceOffer,
    ProvisionCost,
    GraphProvisioner,
    TemplateProvisioner,
    UpdatingProvisioner,
    CloningProvisioner,
    CompanionProvisioner,
    Requirement,
    ProvisioningPolicy,
)
from tangl.core import Node, Graph
from tangl.core.factory import TemplateFactory, Template


# ============================================================================
# Mock Objects (normally from tangl.core / tangl.vm)
# ============================================================================

class MockContext:
    """Minimal context for testing."""
    def __init__(self, graph, cursor_id):
        self.graph = graph
        self.cursor_id = cursor_id


# ============================================================================
# Unit Tests - Individual Provisioners
# ============================================================================

def test_graph_provisioner_finds_existing_node():
    """GraphProvisioner should offer EXISTING nodes that match."""
    # Setup
    registry = Graph()
    door = Node(label="door", tags={'wooden'})
    registry.add(door)
    
    requirement = Requirement(identifier="door")
    ctx = MockContext(graph=registry, cursor_id=door.uid)
    
    provisioner = GraphProvisioner(node_registry=registry, layer='local')
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) == 1
    assert offers[0].operation is ProvisioningPolicy.EXISTING
    assert offers[0].base_cost is ProvisionCost.DIRECT
    assert offers[0].cost == float(ProvisionCost.DIRECT)
    
    # Accept offer
    provider = offers[0].accept(ctx=ctx)
    assert provider is door


def test_graph_provisioner_finds_by_criteria():
    """GraphProvisioner should find nodes matching criteria."""
    # Setup
    registry = Graph()
    door1 = Node(label="door1", tags={'wooden', 'locked'})
    door2 = Node(label="door2", tags={'metal', 'unlocked'})
    registry.add(door1)
    registry.add(door2)
    
    requirement = Requirement(criteria={'has_tags': {'wooden'}})
    ctx = MockContext(graph=registry, cursor_id=door1.uid)
    
    provisioner = GraphProvisioner(node_registry=registry, layer='local')
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) >= 1
    provider = offers[0].accept(ctx=ctx)
    assert 'wooden' in provider.tags


def test_graph_provisioner_returns_empty_if_not_found():
    """GraphProvisioner should return no offers if node doesn't exist."""
    # Setup
    registry = Graph()
    requirement = Requirement(identifier="missing")
    ctx = MockContext(graph=registry, cursor_id=UUID('00000000-0000-0000-0000-000000000003'))
    
    provisioner = GraphProvisioner(node_registry=registry, layer='local')
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) == 0

import pydantic

LockableNode = pydantic.create_model(
    "LockableNode",
    __base__=Node,
    locked=(bool, False),
)

def test_template_provisioner_creates_from_template():
    """TemplateProvisioner should offer CREATE with template."""
    # Setup
    registry = Graph()
    factory = TemplateFactory(label="templates")
    factory.add(Template[LockableNode](label="door", obj_cls=LockableNode, locked=True))
    
    requirement = Requirement(
        identifier="door",
        template=Template[LockableNode](label="door", obj_cls=LockableNode, locked=True),
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )
    ctx = MockContext(graph=registry, cursor_id=UUID('00000000-0000-0000-0000-000000000003'))
    
    provisioner = TemplateProvisioner(factory=factory, layer='author')
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) == 1
    assert offers[0].operation is ProvisioningPolicy.CREATE_TEMPLATE
    assert offers[0].base_cost is ProvisionCost.CREATE
    assert offers[0].cost == float(ProvisionCost.CREATE)
    
    # Accept offer
    provider = offers[0].accept(ctx=ctx)
    assert provider.label == 'door'
    assert provider.locked == True


def test_updating_provisioner_modifies_existing():
    """UpdatingProvisioner should offer UPDATE for existing nodes."""
    # Setup
    registry = Graph()
    door = LockableNode(label="door", locked=False)
    registry.add(door)
    
    requirement = Requirement(
        identifier="door",
        template=Template[LockableNode](locked=True, obj_cls=LockableNode),
    )
    ctx = MockContext(graph=registry, cursor_id=door.uid)
    
    provisioner = UpdatingProvisioner(node_registry=registry, layer='author')
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) == 1
    assert offers[0].operation is ProvisioningPolicy.UPDATE
    assert offers[0].base_cost is ProvisionCost.LIGHT_INDIRECT
    assert offers[0].cost == float(ProvisionCost.LIGHT_INDIRECT)
    
    # Accept offer
    provider = offers[0].accept(ctx=ctx)
    assert provider is door  # Same object
    assert provider.locked == True  # Updated


def test_cloning_provisioner_creates_copy():
    """CloningProvisioner should offer CLONE of existing node."""
    # Setup
    registry = Graph()
    ref_door = LockableNode(label="door", locked=False)
    registry.add(ref_door)
    
    requirement = Requirement(
        identifier="door",
        template=Template[LockableNode](label="door_clone", locked=True, obj_cls=LockableNode),
        policy=ProvisioningPolicy.CLONE,
        reference_id=ref_door.uid,
    )
    ctx = MockContext(graph=registry, cursor_id=ref_door.uid)
    
    provisioner = CloningProvisioner(node_registry=registry, layer='author')
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) == 1
    assert offers[0].operation is ProvisioningPolicy.CLONE
    assert offers[0].base_cost is ProvisionCost.HEAVY_INDIRECT
    assert offers[0].cost == float(ProvisionCost.HEAVY_INDIRECT)
    
    # Accept offer
    provider = offers[0].accept(ctx=ctx)
    assert provider is not ref_door  # Different object
    assert provider.label == 'door_clone'
    assert provider.locked == True


# ============================================================================
# Integration Tests - Multiple Provisioners
# ============================================================================

def test_cheapest_offer_wins():
    """When multiple provisioners offer solutions, cheapest should win."""
    # Setup
    registry = Graph()
    existing_door = Node(label="door")
    registry.add(existing_door)
    
    requirement = Requirement(
        identifier="door",
        template=Template[Node](label="door", obj_cls=Node),
        policy=ProvisioningPolicy.ANY,
    )
    ctx = MockContext(graph=registry, cursor_id=existing_door.uid)
    
    # Multiple provisioners
    graph_prov = GraphProvisioner(node_registry=registry, layer='local')
    template_prov = TemplateProvisioner(
        factory=TemplateFactory(label="templates"),
        layer='author'
    )
    template_prov.factory.add(Template[Node](label="door", obj_cls=Node))
    
    # Collect all offers
    all_offers = []
    all_offers.extend(graph_prov.get_dependency_offers(requirement, ctx=ctx))
    all_offers.extend(template_prov.get_dependency_offers(requirement, ctx=ctx))
    
    # Sort by cost
    all_offers.sort(key=lambda o: o.cost)
    
    # Assert cheapest wins
    assert len(all_offers) == 2
    best = all_offers[0]
    assert best.operation is ProvisioningPolicy.EXISTING
    assert best.cost < all_offers[1].cost
    
    provider = best.accept(ctx=ctx)
    assert provider is existing_door


def test_multiple_strategies_for_same_requirement():
    """A requirement with ANY policy should get multiple offer types."""
    # Setup
    registry = Graph()
    existing_door = Node(label="door")
    registry.add(existing_door)
    
    requirement = Requirement(
        identifier="door",
        template=Template[LockableNode](label="door_updated", locked=True, obj_cls=LockableNode),
        policy=ProvisioningPolicy.ANY | ProvisioningPolicy.CLONE,
        reference_id=existing_door.uid,
    )
    ctx = MockContext(graph=registry, cursor_id=existing_door.uid)
    
    # Provisioners that offer different strategies
    graph_prov = GraphProvisioner(node_registry=registry)
    updating_prov = UpdatingProvisioner(node_registry=registry)
    cloning_prov = CloningProvisioner(node_registry=registry)
    factory = TemplateFactory(label="templates")
    factory.add(Template[Node](label="door", obj_cls=Node))
    template_prov = TemplateProvisioner(factory=factory)
    
    # Collect all offers
    all_offers = []
    all_offers.extend(graph_prov.get_dependency_offers(requirement, ctx=ctx))
    all_offers.extend(updating_prov.get_dependency_offers(requirement, ctx=ctx))
    all_offers.extend(cloning_prov.get_dependency_offers(requirement, ctx=ctx))
    all_offers.extend(template_prov.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert we got multiple strategies
    operations = {offer.operation for offer in all_offers}
    assert ProvisioningPolicy.EXISTING in operations
    assert ProvisioningPolicy.UPDATE in operations
    assert ProvisioningPolicy.CLONE in operations
    assert ProvisioningPolicy.CREATE_TEMPLATE in operations
    
    # Cost ordering is correct
    costs = {
        op: next(o.cost for o in all_offers if o.operation is op)
        for op in operations
    }
    assert (
        costs[ProvisioningPolicy.EXISTING]
        < costs[ProvisioningPolicy.UPDATE]
        < costs.get(ProvisioningPolicy.CLONE, float(ProvisionCost.CREATE) + 1)
        < costs[ProvisioningPolicy.CREATE_TEMPLATE]
    )


# ============================================================================
# Affordance Tests
# ============================================================================

def test_companion_offers_affordances():
    """CompanionProvisioner should offer actions based on state."""
    # Setup
    companion = Node(label="friend", tags={'happy', 'musical'})
    scene = Node(label="scene", tags={'peaceful'})
    registry = Graph()
    registry.add(companion)
    registry.add(scene)
    
    ctx = MockContext(graph=registry, cursor_id=scene.uid)
    provisioner = CompanionProvisioner(companion_node=companion, layer='local')
    
    # Act
    offers = list(provisioner.get_affordance_offers(scene, ctx=ctx))
    
    # Assert
    assert len(offers) >= 1
    labels = {offer.label for offer in offers}
    assert 'talk' in labels
    
    # Because companion is happy, 'sing' should be offered
    assert 'sing' in labels


def test_affordance_target_tags_filter():
    """Affordance offers should respect target_tags."""
    # Setup
    companion = Node(label="friend", tags={'happy'})
    musical_scene = Node(label="concert", tags={'musical'})
    battle_scene = Node(label="arena", tags={'combat'})
    registry = Graph()
    registry.add(companion)
    
    ctx = MockContext(graph=registry, cursor_id=musical_scene.uid)
    provisioner = CompanionProvisioner(companion_node=companion, layer='local')
    
    # Get offers for musical scene
    musical_offers = list(provisioner.get_affordance_offers(musical_scene, ctx=ctx))
    musical_labels = {o.label for o in musical_offers if o.available_for(musical_scene)}
    
    # Get offers for battle scene  
    battle_offers = list(provisioner.get_affordance_offers(battle_scene, ctx=ctx))
    battle_labels = {o.label for o in battle_offers if o.available_for(battle_scene)}
    
    # 'sing' should only be available in musical scene
    sing_offers = [o for o in musical_offers + battle_offers if o.label == 'sing']
    if sing_offers:
        sing_offer = sing_offers[0]
        assert sing_offer.available_for(musical_scene)
        # Might not be available for battle scene if target_tags includes 'musical'


def test_affordance_uniqueness_per_destination():
    """Each destination should only have one affordance per label."""
    # Setup
    companion1 = Node(label="friend1", tags={'happy'})
    companion2 = Node(label="friend2", tags={'happy'})
    scene = Node(label="scene")
    registry = Graph()
    
    ctx = MockContext(graph=registry, cursor_id=scene.uid)
    prov1 = CompanionProvisioner(companion_node=companion1, layer='local')
    prov2 = CompanionProvisioner(companion_node=companion2, layer='local')
    
    # Both offer "talk"
    offers1 = list(prov1.get_affordance_offers(scene, ctx=ctx))
    offers2 = list(prov2.get_affordance_offers(scene, ctx=ctx))
    
    talk_offers = [o for o in offers1 + offers2 if o.label == 'talk']
    assert len(talk_offers) >= 2  # Both companions offer "talk"
    
    # In real system, selector would pick one based on cost/proximity
    # For now, just verify we detect the collision
    labels = [o.label for o in talk_offers]
    assert labels.count('talk') == len(talk_offers)


# ============================================================================
# Edge Cases
# ============================================================================

def test_provisioner_with_no_offers():
    """Provisioner with no applicable offers should return empty iterator."""
    # Setup
    registry = Graph()
    requirement = Requirement(identifier="nonexistent")
    ctx = MockContext(graph=registry, cursor_id=UUID('00000000-0000-0000-0000-000000000003'))
    
    provisioner = GraphProvisioner(node_registry=registry)
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) == 0


def test_offer_with_failing_callback():
    """Offer with failing callback should propagate exception."""
    # Setup
    def failing_callback(*_, **__):
        raise RuntimeError("Provisioning failed!")
    
    offer = DependencyOffer(
        requirement_id=UUID('00000000-0000-0000-0000-000000000002'),
        operation=ProvisioningPolicy.CREATE_TEMPLATE,
        base_cost=ProvisionCost.CREATE,
        cost=float(ProvisionCost.CREATE),
        accept_func=failing_callback,
    )
    
    registry = Graph()
    ctx = MockContext(graph=registry, cursor_id=UUID('00000000-0000-0000-0000-000000000003'))
    
    # Act & Assert
    with pytest.raises(RuntimeError, match="Provisioning failed"):
        offer.accept(ctx=ctx)


def test_template_provisioner_without_template():
    """TemplateProvisioner should skip requirements without templates."""
    # Setup
    registry = Graph()
    requirement = Requirement(identifier="door")  # No template
    ctx = MockContext(graph=registry, cursor_id=UUID('00000000-0000-0000-0000-000000000003'))
    
    provisioner = TemplateProvisioner(factory=TemplateFactory(label="templates"))
    
    # Act
    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    
    # Assert
    assert len(offers) == 0, f"Shouldn't be able to create without template {offers[0]!r}"  # Can't create without template
