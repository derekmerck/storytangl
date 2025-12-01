from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.story.ir import StoryMetadata, StoryScript


def test_script_manager_from_story_script_round_trip() -> None:
    metadata = StoryMetadata(
        id="demo",
        label="Demo",
        world_id="test-world",
        entry_label="start",
    )
    ir = StoryScript(metadata=metadata, blocks={"start": {"text": "Hello"}})

    manager = ScriptManager.from_story_script(ir)
    world = World(label="demo_world", script_manager=manager)

    graph = world.create_story("demo_story")

    assert graph is not None
    assert graph.initial_cursor_id is not None
