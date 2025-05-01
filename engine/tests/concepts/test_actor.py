from __future__ import annotations
import logging
import pytest
import pickle

from tangl.core import Graph, Node, on_gather_context
from tangl.story.concept import Actor, Role


def test_role():
    # Create a Role instance
    role = Role(label="role1", actor_criteria={'alias': 'dummy'})
    # Test initial role state
    assert role.label == "ro-role1"
    # roles automatically append their type to their uid for registry lookup if they
    # don't already start with the correct prefix
    assert role.actor is None

def test_actor1():
    actor = Actor(label="actor1", name="Actor Name")
    assert actor.name == "Actor Name"

def test_actor2():
    # There was a bug in __eq__ that didn't restore the graph after testing equality
    graph = Graph()
    actor = Actor(label="john_doe", name="John Doe", graph=graph)
    role = Role(actor_ref="john_doe", graph=graph)

    print( graph )
    print( actor.graph )
    print( role.graph )

    assert graph, "Graph not created"
    assert actor.graph is graph, "Actor graph is not set properly"
    assert role.graph is graph, "Role graph is not set properly"
    assert actor.graph is role.graph, "Graphs not the same"

    assert actor.label in graph, "Actor key fails"
    assert actor in graph, "Actor not in graph"
    assert role in graph, "Role not in graph"

def test_actor_role_association():
    # Create Actor and Role instances
    g = Graph()
    actor = Actor(label="actor1", name="Fairy Queen", graph=g)
    role = Role(label="role1", graph=g)  # Has to have a graph to dereference it

    # Assign actor to role
    role.cast(actor)

    # Test actor and role after assignment
    assert role.actor == actor
    # assert role in actor.roles

def test_role_set_invalid_actor():
    role = Role(actor_conditions=[])
    with pytest.raises((RuntimeError, KeyError)):
        role.associate_with("Invalid Actor")

@pytest.fixture
def actor_and_role_setup():
    # Uses a basic 'cast_by_ref' setup

    graph = Graph()
    actor = Actor(label="john_doe", name="John Doe", graph=graph)
    role = Role(actor_ref="john_doe", graph=graph)

    # This will pre-cast when role is created
    assert role.actor is actor
    assert role in actor.roles

    return actor, role

def test_actor_role_association_via_role(actor_and_role_setup):
    actor, role = actor_and_role_setup

    if pytest.raises(ValueError):
        assert role.actor is actor

    assert role in actor.roles, "Role should be associated with the actor"
    logging.debug( "disassociating")
    role.disassociate_from(actor)
    assert role.actor is None
    assert role not in actor.roles, "Role should be disassociated from the actor"

def test_actor_role_association_via_actor(actor_and_role_setup):
    actor, role = actor_and_role_setup

    assert role.actor is actor
    assert role in actor.roles, "Role should be associated with the actor"

    print("Disassociating")
    actor.disassociate_from(role)
    assert role.actor is None
    assert role not in actor.roles, "Role should be disassociated from the actor"

def test_role_cast_by_reference(actor_and_role_setup):
    actor, role = actor_and_role_setup

    role.uncast()
    assert role.actor is None, "Actor should be successfully uncast from the role"
    assert role not in actor.roles, "Role should be disassociated from the actor"

    assert role.successor_ref is None, "Role should be cleaned of direct refs"
    assert role.cast(actor) is actor
    assert role.actor == actor, "Actor should be successfully cast for the role"
    assert role in actor.roles, "Role should be associated with the actor"

    role.uncast()
    assert role.cast("john_doe") is actor

@pytest.mark.skip(reason="Not implemented")
def test_cast_by_condition():

    graph = Graph()
    actor = Actor(label="john_doe", name="John Doe", graph=graph)

    assert 'name' in actor.get_namespace()
    assert actor.get_namespace()['name'] == "John Doe"

    role = Role(actor_conditions=["name == 'John Doe'"], graph=graph)
    assert role.cast()
    assert role.actor is actor

# @pytest.mark.xfail(raises=NotImplementedError)
def test_cast_by_template():

    templ = {
        'label': "john_doe",
        'name': "John Doe"
    }
    graph = Graph()
    role = Role(actor_template=templ, graph=graph)
    assert role.cast()
    assert role.actor.name == "John Doe"
    assert 'john_doe' in graph
    assert role.actor.get_namespace().get('name') == "John Doe"

# todo: implement cast-by-cloning
@pytest.mark.skip(reason="not implemented yet")
def test_cast_by_cloning():
    graph = Graph()
    actor = Actor(label="john_doe",
                  name="John Doe",
                  tags=["abc"],
                  graph=graph)

    templ = {
        'label': "john_clone",
        'name': "John Clone",
        'tags': ['is_clone']
    }
    role = Role(actor_ref=actor.label, actor_template=templ, graph=graph)
    assert role.cast()
    assert role.actor.name == "John Clone"
    assert role.actor.has_tags({"abc", "is_clone"}), "Old and new tags not properly unioned in evolution"
    assert 'john_clone' in graph

@pytest.mark.skip(reason="not implemented yet")
def test_role_cast_by_cloning2():

    # Mock index object to simulate story index
    g = Graph()

    # Create Actor and Role instances
    actor = Actor.from_dict(label="actor1", name="Fairy Queen", look={"hair_color": "navy"}, graph=g)
    role = Role.from_dict(label="role1",
                          actor_ref="actor1",
                          actor_template={'name': 'Bob'},
                          graph=g)

    assert role.cast()

    # Test role after casting
    assert role.actor.name == "Bob"
    assert role.actor.look.hair_color.value == "navy"

@pytest.mark.xfail(raises=NotImplementedError)
def test_multiple_role_casting():

    class TestActor(Actor):
        body: int = 9
        mind: int = 9
        charisma: int = 9

        @on_gather_context.register()
        def _include_props(self):
            return {'body': self.body,
                    'mind': self.mind,
                    'charisma': self.charisma}
    # Create a node and add some actors to the index

    graph = Graph()
    actor1 = TestActor(
        label = 'actor1',
        name = "cat",
        body = 10,
        mind = 5,
        graph = graph)
    # graph.add_node(actor1)
    assert actor1 in graph

    # Define a role that references an actor by UID
    role1 = Role(actor_ref='actor1', graph=graph)
    assert role1.actor is actor1

    actor2 = TestActor(
        label = 'actor2',
        name = "dog",
        body = 5,
        mind = 10,
        graph = graph)
    assert actor2 in graph
    assert len( graph.find(has_cls=Actor) ) == 2

    # Define a role that searches for an actor by condition
    role2 = Role(actor_conditions=['body < 8', 'mind > 8'], graph=graph)
    assert role2.actor is actor2

    # Define a role that creates a new actor
    role3 = Role(
        actor_template={
            'obj_cls': TestActor,
            'label': 'actor3',
            'name': 'Sir Bob',
            'body': 15
        },
        graph=graph)
    assert role3.actor.label == 'actor3'
    assert role3.actor.body == 15
    assert role3.actor.mind == 9
    assert len( graph.find_nodes(Actor) ) == 3

    # todo: test cloning
    # # Define a role that evolves an existing actor
    # role4 = Role(uid='role4', actor_reference='actor1', actor_kwargs={'attributes': {'strength': 12}})
    # index.add_node(role4)
    # actor4 = role4.cast()
    # assert actor4.uid == 'actor1'  # It's the same actor, but evolved
    # assert actor4.attributes == {'strength': 12, 'intelligence': 5}

    # Define a role that has no available actors and cannot create a new one
    role5 = Role(label='role5', actor_conditions=['charisma > 10'])
    graph.add_node(role5)
    assert not role5.cast()  # No suitable actor found

def test_actor_pickles():

    a = Actor(name="John Doe")

    s = pickle.dumps( a )
    # print( s )
    res = pickle.loads( s )
    print( res )
    assert a == res

    r = Role(actor_ref=a.uid, graph=a.graph)
    print( r )
    s = pickle.dumps( r )
    # print( s )
    res = pickle.loads( s )
    print( res )
    assert r == res

    assert r.cast()

    s = pickle.dumps( r )
    # print( s )
    res = pickle.loads( s )
    print( res )
    assert r == res


# def test_actor_name():
#
#     a = Actor( name="John Doe", gens="XY" )
#     assert a.titled_full_name == "Mr. John Doe"
#
#     assert( not a.generic )
#
# def test_actor_reduce_defaults():
#
#     for i in range(0, 10):
#         a = Actor( gens=["XX", "XY"] )
#         assert a.gens in [Gens.XX, Gens.XY]
#
#         a = Actor( gens={"XY": 100, "XX": 0} )
#         assert a.gens == Gens.XY
#
# @pytest.mark.parametrize("gens", ["XX", "XY"])
# def test_descs(gens):
#
#     from tangl.actor.desc import kwargs  # type:ignore
#
#     helpers = list( kwargs.keys() )
#     print( helpers )
#
#     a = Actor(gens=gens)
#     for h in helpers:
#         f = getattr(a, h)
#         print( f  )
#
#     if gens == "XX":
#         # check problem w it grabbing lower-case Gens.Xx
#         assert a.gens is Gens.XX
#     if gens == "XY":
#         assert a.gens is Gens.XY
#
#     try:
#         print( a._body_desc() )
#     except TypeError:
#         # ignore if no avatar mixin available
#         pass
#
#     print( a.desc )
#     n = a.gendered_address
#
# def test_actor_goes_by():
#
#     actor = Actor(label="actor1", full_name="Fairy Queen")
#     assert actor.goes_by("Fairy Queen")
#     assert actor.goes_by("Fairy")
#     assert actor.goes_by("Ms. Queen")
