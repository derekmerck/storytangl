"""

"""

import attr

from tangl.utils.attrs import define
from tangl.story import Scene, Action, Actor, Role, Location, Place, Challenge, ChallengeAction, ChallengeRound
from .enums import Move
from .credential import Credential
from .credentialed import Credentialed


@define
class InspectAction(ChallengeAction):
    """Indicate a possible discrepancy in candidate packet"""

    def label(self, **kwargs):
        return f"Inspect {str(self.indicated)}"

    def apply(self, invalidation: Move, credential: Credential, **kwargs):
        credential.inspect( invalidation, **kwargs )

    def follow(self):
        return self.parent


@define
class AllowAction(Action):

    _label: str = "Allow"

    def apply(self):
        self.parent.allow()

    def follow(self):
        return self.parent


@define
class DenyAction(Action):

    _label: str = "Deny"
    def apply(self):
        self.parent.deny()

    def follow(self):
        return self.parent

@define
class ArrestAction(Action):

    _label: str = "Arrest"
    def apply(self):
        self.parent.deny()

    def follow(self):
        return self.parent


@define
class ScreeningChallenge(Challenge):
    # a series of Screening rounds
    game: Game = ScreeningGame


@define
class ScreeningRound(ChallengeRound):

    candidate: Credentialed = None

    # Overrides for generic comments
    on_arrive: str = None
    on_strip: str  = None
    on_search: str = None


    on_invalid_seal: str = None
    on_invalid_date: str = None
    on_incorrect_holder: str = None
    on_incorrect_permit: str = None
    on_incorrect_region: str = None

    on_allow: str = None
    on_deny: str = None
    on_crime: str = None

    def __init_node__(self):
        # add challenge actions
        for move in self.candidate.get_moves():
            self.actions.append( InspectAction( move ) )
        for c in self.candidate.credentials:
            for move in c.get_moves():
                self.actions.append( InspectAction( (move, c) ) )

        self.actions += [
            AllowAction(parent=self),
            DenyAction(parent=self),
            ArrestAction(parent=self)]

    def update_challenge(self):
        pass

@define
class ScreeningRole(Role):
    actor_cls = attr.make_class("CredentialedActor", (), (Actor, Credentialed))

@define
class ScreeningLocation(Location):
    place_cls = attr.make_class(
        "RestrictedPlace",
        ( attr.Attribute(name="extras", type=dict[str, ScreeningRole], default=attr.Factory(dict) ) ),
        (Place, Restricted))

@define
class ScreeningScene(Scene):

    locations: dict[str, ScreeningLocation] = attr.ib(factory=dict)
    roles: dict[str, ScreeningRole] = attr.ib(factory=dict)
