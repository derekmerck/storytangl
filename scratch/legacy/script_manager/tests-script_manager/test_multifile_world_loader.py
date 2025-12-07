import pytest
import tempfile
import os
import yaml
from tangl.world import World
from tangl.script import ScriptManager
from tangl.story.scene import Scene, Block, Action


def create_temp_yaml_files(temp_dir, data):
    for idx, file_scenes in enumerate(data):
        with open(os.path.join(temp_dir, f"scenes_{idx}.yaml"), 'w') as file:
            yaml.dump_all(file_scenes, file)


def test_load_story(sample_world_mf_dicts):
    with tempfile.TemporaryDirectory() as temp_dir:
        create_temp_yaml_files(temp_dir, sample_world_mf_dicts)

        World._instances.clear()
        h = ScriptManager.from_files( files=temp_dir,
                                      sections={'scenes': ['scenes*.yaml']},
                                      metadata={'label': 'test_world',
                                                'title': 'Test World',
                                                'author': 'TanglDev'} )

        h: ScriptManager

        print( h.scenes_data() )
        world = World(label="script_test", script_manager=h)

        for sc_script in world.script.scenes_data():
            print( sc_script)
            sc = world.create_node(base_cls=Scene, **sc_script)
            assert isinstance(sc, Scene)
            for bl in sc.blocks:
                assert isinstance(bl, Block)
