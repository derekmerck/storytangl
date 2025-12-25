from tangl.core.graph import Node
from tangl.story.story_graph import StoryGraph
from tangl.ir.story_ir import BlockScript
from tangl.vm.context import MaterializationContext


def test_materialization_context_creation():
    graph = StoryGraph(label="test")
    template = BlockScript(label="start", content="Start")
    payload = {"label": "start", "content": "Start"}

    ctx = MaterializationContext(
        template=template,
        graph=graph,
        payload=payload,
    )

    assert ctx.template is template
    assert ctx.graph is graph
    assert ctx.payload is payload
    assert ctx.parent_container is None
    assert ctx.node is None


def test_materialization_context_with_parent_container():
    graph = StoryGraph(label="test")
    scene = graph.add_subgraph(label="scene")
    template = BlockScript(label="start", content="Start")

    ctx = MaterializationContext(
        template=template,
        graph=graph,
        payload={},
        parent_container=scene,
    )

    assert ctx.parent_container is scene


def test_materialization_context_payload_mutation():
    graph = StoryGraph(label="test")
    template = BlockScript(label="start", content="Start")
    payload = {"label": "start"}

    ctx = MaterializationContext(
        template=template,
        graph=graph,
        payload=payload,
    )

    ctx.payload["computed"] = True

    assert ctx.payload["computed"] is True


def test_materialization_context_node_lifecycle_assignment():
    graph = StoryGraph(label="test")
    template = BlockScript(label="start", content="Start")

    ctx = MaterializationContext(
        template=template,
        graph=graph,
        payload={},
    )

    assert ctx.node is None

    ctx.node = Node(label="start", graph=graph)

    assert ctx.node is not None
    assert ctx.node.label == "start"
