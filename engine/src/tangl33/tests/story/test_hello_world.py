import logging

from tangl33.core import Graph, Node, Edge, EdgeKind, Domain, HandlerCache, ProviderRegistry, Journal, CursorDriver
from tangl33.story import register_base_capabilities

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_hello_world():

    def build_graph():
        logger.debug("Building Graph")
        a = Node(label="A", locals={"text": "Hello, traveller."})
        b = Node(label="B", locals={"text": "You reach the village."})
        c = Node(label="C", locals={"text": "You look around for an inn."})

        g = Graph(); g.add_all(a, b)
        g.link(a, b, EdgeKind.CHOICE, label="→ Continue")
        g.link(b, c, EdgeKind.CHOICE, trigger="after")

        return g, a.uid

    graph, entry_uid = build_graph()

    cache = HandlerCache(); register_base_capabilities(cache)
    prov  = ProviderRegistry()
    dom   = Domain()
    jour  = Journal()

    driver = CursorDriver(graph, cache, prov, dom, jour)
    driver.cursor_uid = entry_uid

    # -------- cycle 1 --------
    driver.step()                       # resolve reqs (none), render A

    print(driver.cursor_uid)            # still at A (choice edge returned but not auto)
    assert driver.cursor_uid == entry_uid

    print([f.text for f in jour])       # ['Hello, traveller.']
    assert len(jour) == 1, "journal should have 1 entry"

    # manually choose the only outgoing edge
    edge = graph.edges_out[entry_uid][0]
    driver.cursor_uid = edge.dst_uid

    # -------- cycle 2 --------
    driver.step()                       # render B

    assert driver.cursor_uid != entry_uid
    print([f.text for f in jour])       # ['Hello, traveller.', 'You reach the village.']
    assert len(jour) == 2, "journal should have 2 entries"

    # Don't need to select, should continue automatically

    # -------- cycle 3 --------
    driver.step()                       # render B

    assert driver.cursor_uid != entry_uid
    print([f.text for f in jour])       # ['Hello, traveller.', 'You reach the village.', 'You look for an inn']
    assert len(jour) == 3, "journal should have 3 entries"
