from tangl33.core import Node, RenderHandler, render_fragments, Fragment, Tier

def test_render_text_fragment(cap_cache, graph):
    node = Node(label="line", locals={"text": "Hello"})
    graph.add(node)
    cap_cache.register(
        RenderHandler(lambda n, *_: Fragment(text=n.locals["text"], node_uid=n.uid),
                      tier=Tier.NODE, owner_uid=node.uid)
    )
    frags = render_fragments(node, {}, cap_cache)
    assert frags and frags[0].text == "Hello"
