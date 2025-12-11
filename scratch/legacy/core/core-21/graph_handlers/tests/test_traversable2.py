import attr
from uuid import uuid4

from tangl.core import Node, Graph
from tangl.core.mixins import Traversable, Edge
from tangl.utils.journal.models import JournalItemModel

import pytest

TravNode = attr.make_class("TravNode", (), (Traversable, Node))

def test_traversable():

    # Create an instance of the test class
    node = TravNode(conditions=["foo > 5"],
                    effects=["foo = 10"],
                    text="This is a node.",
                    locals={"foo": 0})

    # Check initial state
    assert not node.available()  # entry condition is not satisfied

    # Try to enter the node - should raise an exception
    with pytest.raises( RuntimeError ):
        node.enter()

    # Update namespace
    node.locals.update({"foo": 6})

    # Check updated state
    assert node.available()  # entry condition is now satisfied
    update, next_node = node.enter()
    assert update.text == "This is a node."
    assert next_node is None
    assert node.locals["foo"] == 10  # effect has been applied

    # Call the exit method (currently doesn't do anything)
    with pytest.raises(AttributeError):
        node.exit(None)  # node exit requires an 'edge' argument

def test_revisiting_node():
    node = TravNode(repeats=False, text="This is a node.")
    assert node.num_visits == 0
    assert not node.completed
    update, _ = node.enter()
    assert update.text == "This is a node."
    assert node.num_visits == 1
    assert node.completed


def test_traversable_mixin():

    # Create a test class that uses the TraversableMixin
    @attr.s
    class TestNode(Traversable, Node):
        text: str = attr.ib(default="")

        def render(self, **kwargs):
            return self.text

    # Create an instance of the test class
    node = TestNode(conditions=["foo > 5"],
                    effects=["foo = 10"],
                    text="This is a node.",
                    locals={"foo": 0})

    # Check initial state
    assert not node.available()  # entry condition is not satisfied

    # Try to enter the node - should raise an exception
    try:
        node.enter()
    except Exception as e:
        assert str(e).startswith("Can't enter")

    # Update namespace
    node.locals.update({"foo": 6})

    # Check updated state
    assert node.available()  # entry condition is now satisfied
    assert node.enter() == ('This is a node.', None)  # enter node, apply effects
    assert node.render() == "This is a node."
    assert node.locals["foo"] == 10  # effect has been applied

    with pytest.raises(TypeError):
        # Call the exit method - requires an edge argument
        node.exit()



from pprint import pprint

import attr

from tangl.core import Node, Traversable, Runtime

# import pytest

@attr.define(init=False)
class TraversableNode(Runtime, Traversable, Node):
    pass

def test_traversable():

    n = TraversableNode()
    print( n )
    print( Node.avail(n) )
    print( Runtime.avail(n) )
    print( Traversable.avail(n) )

    assert( n.avail() )
    n.lock()
    assert( not n.avail() )

    n2 = TraversableNode( parent=n, locked=True )
    assert not n2.avail()
    n.unlock(True)
    assert n2.forced
    assert n2.avail()


# @pytest.mark.skip(reason="Not implemented yet")
def test_consumes_str():

    c = TraversableNode(
        conditions=[ "1 + 2 == 3", "True" ],
        continues=[ "somewhere", "nowhere" ]
    )

    print( c.conditions )
    assert c.conditions[0].expr == "1 + 2 == 3"
    print( c.continues )
    assert c.continues[0].ref == "somewhere"


def test_redirects():

    c = TraversableNode(
        uid = "abc",
        redirects = ["abc"]
    )

    print( "c.ind", c._index, c.index )
    print( "c.r[0].ind", c.redirects[0].index )

    assert c.redirect() is c
