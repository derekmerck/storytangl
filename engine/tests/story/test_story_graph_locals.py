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
