from typing import ClassVar

import pytest

from tangl.core.entity import Node, Graph
from tangl.core.handler import HasContext
from tangl.core.solver import Renderable, ContentFragment, on_render_content

class TestNode(Renderable, HasContext, Node):
    content: ClassVar[str] = "Hello, {{ name }}!"

    def __init__(self, label=None):
        super().__init__()
        self.label = label or "test"
        self.locals = {"name": "World"}

    @on_render_content.register(priority=20)
    def add_extra(self, ctx):
        return [{"label": "extra", "content": "extra value"}]

@pytest.mark.xfail(reason="Not working yet")
def test_default_render():
    node = TestNode()
    ctx = {"name": "Alice"}
    frags = TestNode.render_content(node, ctx=ctx)
    assert len(frags) == 2
    assert any(isinstance(f, ContentFragment) for f in frags)
    texts = [f.content for f in frags]
    assert any("Alice" in t for t in texts)

@pytest.mark.xfail(reason="Not working yet")
def test_render_priority():
    node = TestNode()
    ctx = {"name": "Bob"}
    frags = TestNode.render_content(node, ctx=ctx)
    assert len(frags) == 2
    print(f"{[str(f) for f in frags]}")
    # Should include both the default and extra fragment
    assert any(f.content == "Hello, Bob!" for f in frags)
    assert any(f.content == "extra value" for f in frags)

@pytest.mark.xfail(reason="Not working yet")
def test_render_with_missing_var():
    node = TestNode()
    ctx = {}
    frags = TestNode.render_content(node, ctx=ctx)
    # Jinja2 by default just leaves blanks for missing vars
    assert any("Hello, !" in f.content for f in frags)
