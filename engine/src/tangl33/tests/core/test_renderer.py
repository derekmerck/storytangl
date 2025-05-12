from tangl33.core import Node, Graph, Domain, RenderCap, render_fragments, Fragment, Tier

def test_render_text_fragment(graph):
    node = Node(label="line", locals={"text": "Hello"})
    graph.add(node)
    domain = Domain()

    render_cap = RenderCap(lambda n, *_: Fragment(text=n.locals["text"], node_uid=n.uid),
                           tier=Tier.NODE, owner_uid=node.uid)
    domain.handler_layer("render").append(render_cap)

    frags = render_fragments(node, graph, domain, {})
    assert frags and frags[0].text == "Hello"
