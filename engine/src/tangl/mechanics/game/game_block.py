from typing import Type, Protocol

from pydantic import BaseModel

from tangl.core import Entity
from tangl.core.handlers import on_gather_context, on_enter, on_render
from tangl.story.structure import Block
from tangl.type_hints import StringMap

class GameState(BaseModel):
    max_rounds: int = 5
    current_round: int = 0

    max_score: int = -1
    current_score: list[int] = (0,0)

    completed: bool


class Game(Protocol):

    def get_state(self) -> GameState:
        ...

    def get_moves(self):
        ...

    def resolve_move(self, move):
        ...

class GameBlock(Block):

    game_cls: Type[Game]
    game_state: GameState

    @on_render.register()
    def _provide_possible_moves(self, **context):
        ...

    @on_enter.register()
    def _resolve_player_move(self, move):
        ...

    @on_gather_context.register()
    def _provide_game_state(self, **context) -> StringMap:
        return self.game_state.model_dump()
