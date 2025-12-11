from __future__ import annotations

import pydantic
from typing import ClassVar, Any
import warnings
from typing import Iterable, Type
from enum import Enum
from textwrap import dedent

import jinja2
from pydantic import Field, model_validator, field_validator, ConfigDict

from tangl.type_hints import Tags, Strings
from tangl.entity.mixins import NamespaceHandler
from tangl.graph.mixins import TraversalHandler, Edge
from tangl.mechanics.games import Game, GameHandler
from tangl.utils.rejinja import RecursiveTemplate
from tangl.utils.set_dict import SetDict, EnumdSetDict
from tangl.mechanics.games.enums import GameResult
from .action import Action
from .block import Block

Move = Enum | str


class GameMoveAction(Action):

    successor_ref: str = None
    game_move: Move = Field(alias="move")
    payload: str = None  # mutable, container for optional additional data (e.g., from ui)

    # todo: make sure payload gets injected into the handled move by the service manager

    @property
    def successor(self):
        return self.parent

    @field_validator('tags')
    @classmethod
    def _tag_as_dynamic(cls, data: Tags):
        data.add('dynamic')

class ChallengeHandler:

    @classmethod
    def handle_game_action(cls, node: Challenge, action: GameMoveAction) -> Edge:
        # get move from action and payload
        player_move = 123
        result = node.game.handle_player_move(node.game,
                                              player_move=player_move,
                                              data = None)
        if result:
            return result  # type: Edge


class Challenge(Block):
    """
    Challenges are block-wrappers for game mechanic {class}\`.Game\` objects.

    Rendering uses a recursively evaluating template, so nested jinja in included vars is allowed.

    Available ns cues for text rendering:
    - player/opponent_move
    - player_won/lost_game/round
    - player/opponent_score
    - game_round, game_scoring_n (total rounds)
    - player_move_descs, opponent_move_descs, round_result_descs, game_state_descs, opponent_cue_descs
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    DEFAULT_TEXT: ClassVar[str] = dedent("""\
        {{ player_move_descs.choice(player_move) }}
        {{ opponent_move_descs.choice(opponent_move) }}
        {{ round_result_descs.choice(round_result)  }}
        {{ game_state_descs | random }}
        {{ opponent_cue_descs.choice(opponent_next_move) }}
        """)

    # todo: cast move value to appropriate Move enum

    text: str = DEFAULT_TEXT

    player_move_descs: EnumdSetDict[Move, Strings] = Field(default_factory=EnumdSetDict)
    opponent_move_descs: EnumdSetDict[Move, Strings] = Field(default_factory=EnumdSetDict)
    opponent_cue_descs: EnumdSetDict[Move, Strings] = Field(default_factory=EnumdSetDict)
    round_result_descs: EnumdSetDict[GameResult, Strings] = Field(default_factory=EnumdSetDict)

    @pydantic.field_validator('player_move_descs',
                              'opponent_move_descs',
                              'round_result_descs',
                              'opponent_cue_descs', mode="before")
    @classmethod
    def _cast_to_esd(cls, data):
        if isinstance(data, dict):
            return EnumdSetDict(data)
        return data

    game_state_descs: Strings = Field(default_factory=list)

    @property
    def game_actions(self) -> Iterable[GameMoveAction]:
        return self.find_children(GameMoveAction)

    @property
    def game(self) -> Game:  # Hint the game class by overloading in subclasses
        return self.find_child(Game)

    def reset(self):
        if self.game:
            # sometimes a placeholder challenge doesn't have a game defined
            self.game.reset()

    @TraversalHandler.exit_strategy
    def _handle_game_action(self, with_edge: Action) -> Edge:
        if isinstance(with_edge, GameMoveAction):
            return ChallengeHandler.handle_game_action(self, action = with_edge)

    @NamespaceHandler.strategy
    def _include_challenge_content(self):
        return {
            "player_move_descs": self.player_move_descs,
            "opponent_move_descs": self.opponent_move_descs,
            "round_result_descs": self.round_result_descs,
            "game_state_descs":   self.game_state_descs,
            "opponent_cue_descs": self.opponent_cue_descs,
            "reset": self.reset   # method
        }

    @NamespaceHandler.strategy
    def _include_game_ns(self):
        return NamespaceHandler.get_namespace(self.game)

    j2_template_cls: ClassVar[jinja2.Template] = RecursiveTemplate
