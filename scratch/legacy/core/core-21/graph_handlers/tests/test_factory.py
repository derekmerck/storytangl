from __future__ import annotations

from tangl.graph import GraphFactory, Node

import pytest
# pytest.skip(reason="Not yet implemented", allow_module_level=True)

def test_node_factory():

    data = {'label': 'abc',
            'tags': {"tag1", "tag2"}
            }

    node = GraphFactory().create_node(**data)
    print( node )

    assert node.has_tags("tag1")


class TestNode(Node):

    @property
    def cats(self) -> list[TestNode]:
        return [x for x in self.children if isinstance(x, TestNode)]


def test_node_factory_children():
    data = {'label': 'abc',
            'tags': {"tag1", "tag2"},
            'cats': [{
                'label': 'cat1'
            }]
            }

    node = GraphFactory().create_node(base_cls=TestNode, **data)
    print(node)

    assert node.has_tags("tag1")
    assert isinstance(node.cats[0], TestNode)
