import pytest

from tangl.core.entity import Graph, Node, Registry
from tangl.core.solver.provisioner.requirement import HasRequirement
from tangl.core.solver.provisioner.entity_template import EntityTemplate, TemplateProvider

class MockNode(Node):
    name: str
    domain: TemplateProvider = None
    type: str = None

@pytest.fixture
def actor_node():
    graph = Graph()
    domain = TemplateProvider(label="domain_templates")
    domain.template_registry.add(EntityTemplate(data={
        "obj_cls": MockNode,
        "type": "scene",
        "name": "act_1"}))
    return MockNode(name="hero", type="actor", graph=graph, domain=domain)


def test_requirement_resolution_graph_only(actor_node):

    req = HasRequirement(req_criteria={"type": "actor"}, graph=actor_node.graph)
    assert req.resolve_requirement()  # should find this in the graph
    assert req.provider is actor_node

def test_requirement_resolution_domain_template(actor_node):

    class DomainRequirement(HasRequirement):
        domain: TemplateProvider

    req = DomainRequirement(req_criteria={"type": "scene"},
                            graph=actor_node.graph,
                            domain=actor_node.domain)

    assert actor_node.domain.can_provide(**req.req_criteria)

    assert req.resolve_requirement()

    assert req.provider is not None
    assert req.provider.type == "scene"
    assert req.provider.name == "act_1"

def test_requirement_resolution_with_fallback(actor_node):

    req = HasRequirement(req_criteria={"type": "location"}, fallback_template={"obj_cls": MockNode, "type": "location", "name": "default_room"}, graph=actor_node.graph)

    assert req.resolve_requirement()
    assert req.provider is not None
    assert req.provider.type == "location"
    assert req.provider.name == "default_room"
