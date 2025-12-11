
from tangl.story.world import WorldHandler

def test_world_creation(world):
    print( world )

def test_world_info(world):
    info = WorldHandler.get_world_info('test_world')
    print(info)

def test_world_list(world):
    result = WorldHandler.get_world_list()
    print(result)

def test_story_creation(world):
    from tangl.story.scene import Scene, Block
    from tangl.story.actor import Actor

    story = WorldHandler.create_story(world)
    print(story.nodes)

    assert story.world is world

    node = story.get_node('first_scene')
    assert isinstance(node, Scene)

    assert node.world is world

    node = story.get_node('first_scene/start')
    assert isinstance(node, Block)

    node = story.get_node('actor1')
    assert isinstance(node, Actor)

def test_scene_list(world):

    ls = WorldHandler.get_scene_list('test_world')
    assert 'first_scene' in [ l.key for l in ls ]
    assert 'Scene 1' in [ l.value for l in ls ]
