import pytest
import logging

from tangl.story.structure import Block
from tangl.story.story_graph import Story

logger = logging.getLogger(__name__)

def test_create_block():
    b = Block( content="I'm a block" )
    print( b )
    assert b.content == "I'm a block"
    print( b.render() )
    assert b.render()['content'] == "I'm a block"


def test_block():
    story = Story()
    # Create a Block with conditions and effects
    block = Block(conditions=["foo > 5"],
                  effects=["foo = 10"],
                  content="This is a block.",
                  locals={"foo": 0},
                  graph=story)

    # Check initial state
    assert not block.available(), "entry condition should not be satisfied"
    assert block.effects

    # Update namespace
    block.locals.update({"foo": 6})

    # Check updated state
    assert block.available(), "entry condition should be satisfied"

    # StoryHandler.goto_node(block.story, block.uid)
    # assert block.locals["foo"] == 10, "effect should be applied"

    # update = StoryHandler.get_update(story)
    # assert update[0].text == "This is a block."


def test_block_actions():

    from tangl.story.structure import Action

    story = Story()
    block = Block(content="Test block", graph=story)
    target = Block(content="Target block", graph=story)

    # Create some Actions
    action1 = Action(content="Action 1", next=target.uid, predecessor=block)
    action2 = Action(content="Action 2", next=target.uid, predecessor=block)
    action3 = Action(content="Action 3", next=target.uid, predecessor=block)

    # # Add Actions as children of the Block
    # block.add_child(action1)
    # block.add_child(action2)
    # block.add_child(action3)

    # Check actions
    choices = list( block.actions )
    assert len(choices) == 3, "Should be three choices"
    assert choices[0] is action1

def test_action_activation_modes():

    from tangl.story.structure import Action

    story = Story()
    block = Block(content="Test block", graph=story)
    target = Block(content="Target block", graph=story)

    # Create some Actions
    action1 = Action(content="Action 1", next=target.uid, predecessor=block)
    action2 = Action(content="Action 2 (redir)", next=target.uid, activation="first", predecessor=block)
    action3 = Action(content="Action 3 (cont)", next=target.uid, activation="last", predecessor=block)

    # Check actions
    choices = list( block.actions )
    assert len(choices) == 1, "Should be one choice"
    assert choices[0] is action1

    # Check redirects
    redirects = list( block.redirects )
    assert len(redirects) == 1, "Should be one redirect"
    assert redirects[0] is action2
    assert block._check_for_redirect() == action2

    # Check continues
    continues = list( block.continues )
    assert len(continues) == 1, "Should be one continue"
    assert continues[0] is action3
    assert block._check_for_continue() == action3


# from textwrap import dedent
# from pprint import pprint
#
# def test_dialog_blocks():
#
#     text = dedent( """
#     > [!MC.pleased] Main Character
#     > Hello there!
#
#     She waves back at you.
#     """ )
#
#     block = Block(text=text,
#                   locals={"foo": 0})
#
#     r = block.render()
#     pprint( r )
#
#     assert r.dialog
#     assert len(r.dialog) == 2
#     assert r.dialog[0].style_class == "MC.pleased"


def test_block_render_with_actor_name():
    from tangl.story.story_graph import Story
    from tangl.story.structure import Scene
    from tangl.story.concept import Role, Actor
    story = Story()
    scene = Scene(label="scene1", graph=story)
    role = Role(label="role1", actor_template={'obj_cls': 'Actor', 'label': 'john', 'name': 'John Doe'}, graph=scene.story)

    logger.debug(role)

    scene.add_child(role)
    block = Block(label="block1", content=r"Hello, {{ ro_role1.name }}!", graph=scene.story)
    scene.add_child(block)

    logger.debug(scene.graph.nodes_by_path)
    logger.debug(scene.gather_context())
    logger.debug(block.gather_context())

    rendered_output = block.render()['content']
    expected_output = "Hello, John Doe!"

    assert rendered_output == expected_output

# def test_block():
#     block = Block(uid="block1", text="Block Text")
#     assert block.text == "Block Text"
#     assert len(block.actions) == 0
#
#     action = Action(uid="action1", label="Action Label", next_block="next_block1")
#     block.add_action(action)
#     assert len(block.actions) == 1
#     assert block.actions[0] == action
#     assert action.parent == block
#
# def test_block_with_assets():
#     block = Block(uid="block1", text="You find {{ asset1.description }}")
#     asset = Asset(uid="asset1", description="a shiny sword")
#     block.add_asset(asset)
#
#     rendered_text = block.render()
#     assert rendered_text == "You find a shiny sword"

#
# def test_create_block():
#     story = Story()
#     menu = MenuBlock( graph=story, with_tags=['my_menu'] )
#     block1 = Block( tags=['my_menu'], graph=story )
#     block2 = Block( tags=['my_menu'], graph=story )
#
#     print( menu.actions )
#
#     assert menu.actions[0].successor == block1
#     assert menu.actions[1].successor == block2

