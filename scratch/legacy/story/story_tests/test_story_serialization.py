import pickle

import pytest

from tangl.core.utils.cattrs_converter import NodeConverter
from tangl.core import Node

# Node._subclass_map.clear()

from tangl.story import Story
from tangl.story.story_node import StoryNode
from tangl.story.scene import Scene, Block
from tangl.story.actor import Actor, Role
from tangl.story.asset import Asset
from tangl.story.asset.wearable import Wearable


def test_node_subtype():
    k = StoryNode(label="Test Node k")
    print( k )
    cc = NodeConverter()
    k_ = cc.unstructure(k, Node )
    print( k_ )
    kk = cc.structure(k_, Node )
    print( kk )
    assert isinstance(kk, StoryNode)
    assert k == kk
    assert k is not kk

# subtypes can get messed up by world classes if they use the same name...
# from ld1 import world
# from ac1 import world



@pytest.mark.xfail(reason="Player is not handled properly in the graph teardown and setup (nor is world or bookmark)")
def test_registry_subtype():
    r = Story()
    r.player.full_name = "Bob Smith"
    k = StoryNode(label="Test Node k")
    print( k )
    r.add_node(k)
    cc = NodeConverter()
    r_ = cc.unstructure(r)
    print( r_ )
    rr = cc.structure(r_, Story)
    print( rr )
    assert isinstance(rr, Story)
    assert k in rr
    kk = rr.get( k.guid )
    assert kk is not k

    print( r.world )
    print( rr.world )
    assert rr.world == r.world

    print( r.player.pm )
    print( rr.player.pm )
    assert rr.player == r.player

def test_various_node_subtypes():
    g = Story()
    s = Scene(label="scene1", graph=g)
    r = Role(label="role1", graph=g, actor_ref="abc")
    s.add_child(r)
    b = Block(label="block1", graph=g)
    s.add_child(b)

    cc = NodeConverter()

    s_flat = cc.unstructure(s)
    print( s_flat )
    ss = cc.structure( s_flat, Scene )
    print( ss.children )
    cc.relink_node(ss, g)
    assert ss == s

    b_flat = cc.unstructure(b)
    bb = cc.structure(b_flat, Block)
    r_flat = cc.unstructure(r)
    rr = cc.structure(r_flat, Role)
