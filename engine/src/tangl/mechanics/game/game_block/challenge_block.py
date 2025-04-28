from tangl.type_hints import StringMap
from tangl.core import NamespaceHandler
from tangl.story.scene import Block, Action
from tangl.mechanics.games import Game

class ChallengeBlock(Block):
    """
    Challenge blocks are wrappers for "Game" interactions.

    Games have moves and win/lose conditions.  They may take place over multiple _rounds_,
    within a single story _turn_.  This is modeled by repeatedly visiting the same block
    until the game is resolved.
    """

    @property
    def game(self) -> Game:
        return self.find_child(Game)

    @property
    def actions(self) -> list[Action]:
        return super().actions + [ Action.from_nodes(self, m) for m in self.game.get_moves() ]
        # todo: this isn't quite right -- need to return the same action with a payload, not create totally new actions each round

    @NamespaceHandler.strategy()
    def _include_game_status(self, **kwargs) -> StringMap:
        return self.game.get_status()

