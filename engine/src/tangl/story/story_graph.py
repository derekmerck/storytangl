
from typing import ClassVar
from uuid import UUID

from pydantic import field_serializer, field_validator

from ..type_hints import StringMap
from tangl.core import Graph
from .dispatch import story_dispatch
from .fabula import World


class StoryGraph(Graph):
    # A subclass of graph that knows that it is a story and who its author is

    world: World | None = None
    initial_cursor_id: UUID | None = None

    def get_active_layers(self):
        layers = { story_dispatch }
        if self.world and hasattr(self.world, "get_active_layers"):
            layers.update(*self.world.get_active_layers())
        return layers

    # todo: there is definitely a more clever way to auto infer recursive
    #       structuring for entities
    @field_serializer("world")
    @classmethod
    def _dump_world(cls, data: World):
        if data is not None:
            return data.unstructure()

    @field_validator("world", mode="before")
    @classmethod
    def _structure_world(cls, value: dict):
        if isinstance(value, dict):
            return World.structure(value)
        elif isinstance(value, World):
            return value
        elif value is None:
            return None
        raise ValueError(f"World {value} is not a valid data, World, or None")

