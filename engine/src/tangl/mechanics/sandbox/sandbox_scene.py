from __future__ import annotations

from tangl.story.structure.scene import Scene
from tangl.story.concept.actor import Actor

from .sandbox import Sandbox, MobileNode, ScheduledNode

class SandboxScene(Sandbox, Scene):

    @property
    def events(self) -> list[Event]:
        return self.get_children(Event)


class Event(ScheduledNode, Scene):
    pass


class MobileActor(MobileNode, Actor):
    pass
