
from tangl34.core.handlers.provision.requirement import Requirement
from tangl34.story.episodic_process.resource_anchors import Actor, Location, Asset

class Setting(Requirement[Location]):
    ...

class CharacterRole(Requirement[Actor]):
    ...

class Prop(Requirement[Asset]):
    ...
