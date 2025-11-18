from __future__ import annotations

from typing import Any
from uuid import uuid4

from tangl.story.concepts.actor.actor import Actor
from tangl.story.concepts.actor.role import Role
from tangl.story.episode.scene import Scene
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World


def _build_world(script: dict[str, Any]) -> World:
    World.clear_instances()
    manager = ScriptManager.from_data(script)
    return World(label=f"world_{uuid4().hex}", script_manager=manager)


def test_scene_roles_materialize_placeholders() -> None:
    script = {
        "label": "role_placeholder",
        "metadata": {"title": "Role Placeholder", "author": "Tester"},
        "scenes": {
            "throne_room": {
                "blocks": {
                    "start": {
                        "obj_cls": "tangl.story.episode.block.Block",
                    },
                },
                "roles": {
                    "king": {},
                },
            }
        },
    }

    world = _build_world(script)
    story = world.create_story(f"story_{uuid4().hex}")

    scene = story.find_one(label="throne_room", is_instance=Scene)
    assert scene is not None

    roles = scene.roles
    assert len(roles) == 1

    role = roles[0]
    assert isinstance(role, Role)
    assert role.actor is None
    assert role.satisfied is False

    graph_role = story.find_one(label="king", is_instance=Role)
    assert graph_role is role


def test_scene_roles_link_referenced_actor() -> None:
    script = {
        "label": "role_with_actor",
        "metadata": {"title": "Role With Actor", "author": "Tester"},
        "actors": {
            "king_actor": {
                "name": "The King",
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
            },
        },
        "scenes": {
            "throne_room": {
                "blocks": {
                    "start": {
                        "obj_cls": "tangl.story.episode.block.Block",
                    },
                },
                "roles": {
                    "king": {
                        "actor_ref": "king_actor",
                    },
                },
            }
        },
    }

    world = _build_world(script)
    story = world.create_story(f"story_{uuid4().hex}")

    actor = story.find_one(label="king_actor", is_instance=Actor)
    assert actor is not None

    scene = story.find_one(label="throne_room", is_instance=Scene)
    assert scene is not None

    roles = scene.roles
    assert len(roles) == 1

    role = roles[0]
    assert isinstance(role, Role)

    # Link everything (requires frontier includes cursor)
    from tangl.vm import Frame, ResolutionPhase as P
    frame = Frame(graph=story, cursor_id=story.initial_cursor_id)
    assert frame is not None
    frame.run_phase(P.PLANNING)
    frame.run_phase(P.UPDATE)

    assert role.actor is actor
    assert role.satisfied is True
