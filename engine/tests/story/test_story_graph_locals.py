"""Story globals survive constructor-form persistence after in-place changes."""
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story.story_graph import StoryGraph


def test_default_story_locals_round_trip_and_elide_when_cleared() -> None:
    graph = StoryGraph()
    assert "locals" not in graph.unstructure()
    graph.locals["marker"] = {"count": 1}
    data = graph.unstructure()
    assert data["locals"] == {"marker": {"count": 1}}
    assert StoryGraph.structure(data).locals == graph.locals
    encoded = Json.serialize(data)
    restored = StoryGraph.structure(Json.deserialize(encoded))
    assert restored.locals == graph.locals
    graph.locals.clear()
    assert "locals" not in graph.unstructure()
    assert StoryGraph.structure(Json.deserialize(Json.serialize(graph.unstructure()))).locals == {}


def test_owner_patch_preserves_live_world_and_runtime_state() -> None:
    from tangl.story import InitMode, World
    from tangl.vm.replay import Patch, get_replay_engine

    world = World.from_script_data(script_data={
        "label": "locals_patch_world", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {"start": {"content": "Hello"}}}},
    })
    graph = world.create_story("locals_patch_story", init_mode=InitMode.EAGER).graph
    after = StoryGraph.structure(graph.unstructure())
    after.locals["marker"] = "saved"
    delta = get_replay_engine("diff_v1").build_delta(before_graph=graph, after_graph=after)
    flattened = Json.deserialize(Json.serialize(delta.unstructure()))
    flattened["kind"] = Patch
    delta = Patch.structure(flattened)
    members = list(graph.values())
    wiring = graph.wired_node_ids
    assert delta.apply_to(graph) is graph
    assert graph.factory is world and graph.locals == {"marker": "saved"}
    assert graph.wired_node_ids is wiring
    assert list(graph.values()) == members
    assert all(member.registry is graph for member in graph.values())
    assert graph.value_hash() == after.value_hash()
