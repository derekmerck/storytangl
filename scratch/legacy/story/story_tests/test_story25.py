from typing import Mapping
import pickle

import attr

from tangl.story import Block, Story, StoryNode
from tangl.world.world import World

import pytest
from conftest import TEST_WORLD_PATH

@pytest.fixture
def wo():
    return World.load_world( TEST_WORLD_PATH )

@pytest.fixture
def ctx(wo: World):
    return wo.new_story()


class TemplatedStory(Story):

    @property
    def template_maps(self) -> Mapping:
        print("checking maps")
        return {"dog": {"a": -1000},
                "cat": {"a": 10000}}

@attr.define(init=False)
class TestStoryNode(StoryNode):
    a: int = 100

def test_story_node_takes_templates_from_story():

    assert 'dog' in TemplatedStory().template_maps
    print( TestStoryNode )

    el = TestStoryNode(index=TemplatedStory())
    print( el.index.template_maps )
    assert el.a == 100

    el = TestStoryNode(templates=["dog"], index=TemplatedStory())
    assert el.a == -1000


def test_new_story(wo):
    ctx = wo.new_story()
    print(ctx)
    assert 'main_menu/start' in ctx


def test_new_story_bookmark( ctx ):

    # bookmark
    print( list( ctx.by_path.keys() ) )
    print( ctx.bookmark )

    assert( isinstance(ctx.bookmark, Block ) )
    assert( ctx.bookmark.path == "main_menu/start" )
    assert ctx["main_menu/start"] == ctx.bookmark

def test_new_story_blocks_and_actions(ctx):

    # blocks and actions
    assert( "main_menu/start" in ctx )
    assert( "main_menu/start/ac0" in ctx )
    assert( ctx['main_menu/start/ac0'].story == ctx )

def test_new_story_ns(ctx):

    # namespace
    print( ctx.ns() )
    assert( ctx.ns()['turn'] == 0 )

    # globals
    assert ctx.globals['cash'] == 100
    assert ctx.ns()['cash'] == 100
    assert ctx.bookmark.ns()['cash'] == 100


def test_new_story_casting(ctx):

    # casting
    print( ctx['first_role'])
    assert ctx['first_role'].full_name == "Bob"

    # templated role casting
    print( ctx['sample'])
    assert ctx['second_role'].full_name == "Test Person"

    actors = ctx.get_actors()
    print( actors )
    assert 'Test Person' in [ a.full_name for a in actors ]


def test_story_runtime( wo ):

    ctx = wo.new_story( globals={"dog": "cat"} )

    assert ctx.globals['dog'] == "cat"
    assert ctx.ns()['dog'] == "cat"

    from tangl.core import Runtime
    from tangl.utils.attrs import define

    @define
    class RuntimeStoryNode(Runtime, StoryNode):
        pass

    E = RuntimeStoryNode( effects=["dog = 'bird'"], index=ctx )
    E.apply()

    print( ctx.globals )
    assert ctx.globals['dog'] == "bird"


def test_story_pickles():
    wo = World(uid="wo1")
    st = Story(world=wo)
    n = StoryNode(uid="node1", index=st)

    s = pickle.dumps(wo)
    wo2 = pickle.loads( s )
    assert wo == wo2

    s = pickle.dumps( n )
    n2 = pickle.loads( s )
    print( n2 )
    assert n == n2

    s = st.dumps()
    st2 = Story.loads( s )
    print( st2 )
    assert st == st2

    st = wo.new_story()
    s = st.dumps()
    st2 = Story.loads( s )
    print( st2 )
    assert st == st2


def test_live_story_pickles( wo ):

    s = pickle.dumps(wo)
    wo2 = pickle.loads( s )
    assert wo == wo2

    st = Story(world=wo)
    n = StoryNode(uid="node1", index=st)

    s = pickle.dumps( n )
    n2 = pickle.loads( s )
    print( n2 )
    assert n == n2

    s = st.dumps()
    st2 = Story.loads( s )
    print( st2 )
    assert st == st2

    st = wo.new_story()
    s = st.dumps()
    st2 = Story.loads( s )
    print( st2 )
    assert st == st2
