from tangl.story.scene import Challenge
from tangl.story.actor import Actor
from .cred_check_game import CredCheckGame

class CredCheckChallenge(Challenge):

    def candidate(self) -> Actor:
        # For type hinting, this will typically be assigned by the scene handler
        return self.find_child(Actor)

    @property
    def game(self) -> CredCheckGame:
        # Just for type hinting
        return super().game
