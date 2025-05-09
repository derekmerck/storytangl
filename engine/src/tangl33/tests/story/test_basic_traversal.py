from legacy_src.journal.journal_handler import Journal
from tangl33.core import Graph, EdgeKind, HandlerCache, ProviderRegistry, Journal, CursorDriver
from tangl33.story import StoryNode, Domain

def test_basic_traversal():
    """Test basic story graph traversal."""
    # Create a minimal test story
    node_a = StoryNode(label="A", locals={"text": "Node A"})
    node_b = StoryNode(label="B", locals={"text": "Node B"})

    graph = Graph()
    graph.add(node_a)
    graph.add(node_b)
    graph.link(node_a, node_b, EdgeKind.CHOICE)

    # Create minimal runtime
    cache = HandlerCache()
    reg = ProviderRegistry()
    journal = Journal()
    domain = Domain()

    # Register minimal capabilities
    register_base_capabilities(cache)

    # Create driver
    driver = CursorDriver(graph, cache, reg, domain, journal)
    driver.cursor_uid = node_a.uid

    # Step once
    driver.step()

    # Verify journal has Node A's content
    assert len(journal) > 0
    assert any(f.text == "Node A" for f in journal)

    # Choose the edge to Node B
    edges = graph.edges_out.get(node_a.uid, [])
    driver.cursor_uid = edges[0].dst_uid

    # Step again
    driver.step()

    # Verify journal has Node B's content
    assert any(f.text == "Node B" for f in journal)