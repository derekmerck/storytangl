import pydantic

from tangl.graph import Graph
from tangl.story.scene import Action, Block

import pytest

def test_create_action():
    action = Action(label="action1", text="Action Label", successor_ref="next_block1")
    assert action.text == "Action Label"
    assert action.successor_ref == "next_block1"


def test_action():

    g = Graph()
    # Create a test Block
    block = Block(conditions=["foo > 5"], locals={"foo": 0, "action_text": "Go to block"}, label="block1", graph=g)

    # Create an Action from the TestBlock
    action = Action.from_node( block )

    # Check initial state
    assert action.successor == block           # action target is correct
    assert action.text == "Go to block"          # action label set correctly
    assert not action.available()                # entry condition is not satisfied

    # Update namespace
    block.locals.update({"foo": 6})

    # Check updated state
    assert action.available()  # entry condition is now satisfied


def test_missing_target_node():

    with pytest.raises(pydantic.ValidationError):
        action_without_target = Action(
            successor_ref = None,
            locals={"foo": 6}
        )


# def test_action():
#     from tangl.core import NodeIndex
#     story = NodeIndex()
#
#     a = Action( label="I'm an action", ref="my_block", index=story  )
#     print( a )
#     pprint( a.label() )
#
#     b = Block( uid="my_block", index=story )
#     print( b )
#     print( a.follow() )
#
#     assert a.follow() is b
