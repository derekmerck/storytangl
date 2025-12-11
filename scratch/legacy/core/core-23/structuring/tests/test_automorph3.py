# No longer supported

from __future__ import annotations
from typing import *
from enum import Enum

import attr

from tangl.core.node import NodeContext, AutoMorph, reduce_default
from tangl.core.story_node import StoryContext, StoryNode

@AutoMorph.define
class Node1(AutoMorph):
    data_dict: Dict[str, Node1] = attr.ib(factory=dict)
    data_list: List[Node1] = attr.ib(factory=list)

class MyEnum(Enum):
    A = "a"
    B = "b"

@AutoMorph.define
class Node2(Node1):
    node2_dict: Dict[str, Node2] = attr.ib(factory=dict)
    node2_list: List[Node2] = attr.ib(factory=list)

    node0_list: List[Node1] = attr.ib(factory=list)

    my_enum: MyEnum = attr.ib(default=10)

def test_node():

    # print( attr.fields(Node2) )

    n = Node1(_cls="Node2",
              uid="blah2",
              data_list=[{'_cls': Node2, 'uid': 'blah2'}],
              node2_list=[{'uid': 'blah'}], my_enum="b")
    print(n.node2_list[0].path)

    Node2.add_template('template1', {'data_list': [{'uid': 'templ1'}, {}, {}], 'my_enum': 'b'})

    n2 = Node2(templates=['template1'])
    print(n2)

    print(n.context.keys())
    print(n.context._by_path.keys())

    assert 'blah2' in n.context
    assert 'blah2/blah' in n.context
    assert n.pid in n.context
    assert n.node2_list[0].pid in n.context

@StoryNode.define
class Story1(StoryNode):
    children: List[StoryNode] = attr.ib( factory=list )
    var3: int = attr.ib( default=[100, 200], metadata={"reduce": True} )

def test_story_node():

    print( [x.name for x in attr.fields( Story1 ) ])

    Story1.add_template( 'blah', {'locals': {'var1': 10}, 'children': [{'uid': 'ch01'}]})
    s = Story1(templates=["blah"])
    s.globals['var2'] = 100
    assert s.ns()['var1'] == 10
    assert s.ns()['var2'] == 100
    print( s.get_template( 'blah' ) )
    print( s.context.data )

    assert 100 <= s.var3 <= 200

    t = Story1( var3=[1000, 2000] )
    assert 1000 <= t.var3 <= 2000

    Story1.add_template( 'blah2', {'var3': [2000, 3000]})

    t = Story1( templates=['blah2'])
    assert 2000 <= t.var3 <= 3000


if __name__ == "__main__":
    test_node()

    test_story_node()
