"""Token-local nested state has stable constructor form across restoration."""
from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from tangl.core import Graph, Singleton, Token
from tangl.core.bases import Unstructurable
from tangl.persistence.serializers import JsonSerializationHandler as Json


class State(BaseModel):
    current: int
    maximum: int = 100
    note: str = "default"
    markers: list[str] = Field(default_factory=list)


class Embedded(Unstructurable):
    markers: list[str] = Field(default_factory=list, json_schema_extra={"include": True})


class Definition(Singleton):
    state: State | None = Field(default=None, json_schema_extra={"instance_var": True})
    active: bool = Field(default=False, json_schema_extra={"instance_var": True})
    embedded: Embedded = Field(default_factory=Embedded, json_schema_extra={
        "instance_var": True, "unstructurable": True, "include": True,
    })


def test_nested_token_state_is_canonical() -> None:
    definition = Definition(label=f"token-{uuid4()}", state=State(current=3), active=True)
    graph = Graph()
    token = Token[Definition](token_from=definition.label, registry=graph)
    other = Token[Definition](token_from=definition.label, registry=graph)
    explicit = Token[Definition](token_from=definition.label, registry=graph, active=False,
                                 state=State(current=2))
    token.state.current = 2
    token.state.markers.append("changed")
    token.embedded.markers.append("embedded")
    for through_json in (False, True):
        before = graph.unstructure()
        if through_json:
            before = Json.deserialize(Json.serialize(before))
        restored = Graph.structure(before)
        result = restored.get(token.uid)
        assert result.reference_singleton is definition
        assert result.state.current == 2 and result.state.markers == ["changed"]
        assert result.embedded.markers == ["embedded"]
        assert restored.get(other.uid).state.current == 3
        assert restored.get(other.uid).state.markers == []
        assert restored.get(explicit.uid).active is False
        assert restored.get(explicit.uid).state.current == 2
        assert restored.unstructure() == graph.unstructure()
        assert restored.value_hash() == graph.value_hash()
