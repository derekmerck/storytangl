from pydantic import BaseModel

from tangl.scripting import BaseScriptItem
from tangl.story.scene import BlockScript, ActionScript

class GameScript(BaseScriptItem):

    # attach a game handler to a generic game or use obj_cls
    # to set the game to a subtype with a dedicated handler
    game_handler_cls: str = None

    scoring_n: int = 3
    scoring_strategy: str = "best_of_n"

    opponent_move_strategy: str = "make_random_move"
    opponent_revise_move_strategy: str = None


class ChallengeScript(BlockScript):
    """
    Challenge blocks loop back to themselves in the continues stage after evaluating
    each move.

    The `on_won` and `on_lost` fields are aliases to continue actions with implicit
    conditions `game_result is R.WON` or `game_result is L.LOST` respectively.  As
    usual, you can create a list of possible results and the explicit conditions will
    be checked in order.  If you provide multiple possibilities, the last should have no
    explicit conditions, so it always matches based on the game state.

    on_won:
    - label: you won
      target_id: secret_block
      conditions: [ won by a lot ]

    - label: you won
      target_id: winning_block

    on_lost:
    - label: you lost
      target_id: lost_block
    """

    game: GameScript

    # if multiple, the last entry should have no conditions
    on_won: list[ActionScript]
    on_lost: list[ActionScript]
    on_draw: list[ActionScript] = None   # Not required if draw is not possible
