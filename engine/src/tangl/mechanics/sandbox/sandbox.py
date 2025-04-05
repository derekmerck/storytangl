from tangl.core.handlers import HasConditions
from tangl.core.graph import DynamicEdge
from tangl.story.concept.place import Location, Place
from tangl.story.concept.actor import Role, Actor


class SandboxConnection(HasConditions, DynamicEdge):
    # conditions, start-end
    ...

class SandboxZone(Place):

    connections: list[SandboxConnection]

    public: bool = True  # zones are always public

    @property
    def places(self) -> list[Place]:
        return self.find_children(SandboxPlace)

    def actors_present(self):
        res = set()
        for place in self.places:
            res.update(place.actors_present())
        return res

class SandboxPlace(Place):

    public: bool = False  # places can be private, public places are private if closed

    @property
    def zone(self):
        return self.parent

    def actors_present(self):
        return self.story.find(Actor, current_location=self)

    def is_alone(self, actor: Actor) -> bool:
        if self.public:
            return False
        if self.actors_present() == { actor }:
            return True

class SandboxSchedule:
    ...
