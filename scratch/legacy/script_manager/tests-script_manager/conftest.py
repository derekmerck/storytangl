import attr
import pydantic
import pytest
import yaml

@pytest.fixture
def sample_world_mf_dicts():
    return [
        [
            {
                "label": "scene_1",
                "blocks": {
                    'block_1':
                    {
                        "text": "You are in a mysterious forest. There's a path leading north and another one leading south.",
                        "actions": [
                            {"label": "north", "text": "Go north", "target_ref": "block_2"},
                            {"label": "south", "text": "Go south", "target_ref": "block_3"}
                        ]
                    },
                    'block_2':
                    {
                        "text": "You find yourself surrounded by fairies.",
                        "actions": [
                            {"label": "interact", "text": "Interact with the fairies", "target_ref": "block_4"},
                            {"label": "ignore", "text": "Ignore them and continue north", "target_ref": "block_5"}
                        ]
                    },
                    # More blocks...
                }
            },
            {
                "label": "scene_2",
                "blocks": {
                    "block_1": {
                        "text": "You enter a neon-lit city. Cybernetic enhancements are commonplace here.",
                        "actions": [
                            {"label": "explore", "text": "Explore the city", "target_ref": "block_2"},
                            {"label": "leave", "text": "Leave the city", "target_ref": "block_3"}
                        ]
                    },
                    # More blocks for scene 2...
                },
            }
        ],
        [
            {
                "label": "scene_3",
                "blocks": {
                    "block_1": {
                        "text": "You find yourself in a high-tech lab. There's a robot on a workbench.",
                        "actions": [
                            {"label": "examine", "text": "Examine the robot", "target_ref": "block_2"},
                            {"label": "ignore", "text": "Ignore the robot", "target_ref": "block_3"}
                        ]
                    },
                    # More blocks for scene 3...
                }
            },
            # More scenes for the second file...
        ]
    ]