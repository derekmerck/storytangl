from typing import Protocol, Callable, Tuple, Any
from enum import Enum
from collections import Counter

from .type_hints import UniqueString
from .entity import HasContext, Entity, Registry, TaskHandler, HasConditions, Criteria, EntityMixin
from .story_nodes import Block, DynamicAsset, TradeManager, FungibleAsset, AssetType, HasFungibleAssets

# --------------
# Game Mechanics
# --------------
GameStrategy = Callable
GameMove = str | Enum

class Game(HasContext, Entity):

    strategy_registry: Registry[GameStrategy]

    def reset_game_state(self): ...
    def set_opponent_strategy(self, strategy: UniqueString): ...
    def get_player_moves(self) -> list[GameMove]: ...
    def do_player_move(self, move: GameMove, **move_kwargs): ...

GameHandler = TaskHandler

class GameBlock(Block):
    game: Game

# todo: specific game types, token, cards, etc.

# --------------
# Stat Mechanics
# --------------
class StatDomain(AssetType): ...
class Quality(float, Enum):
    qv: Enum
    fv: float

QualityDelta = Quality  # up-up, up, normal, down, down-down
Outcome = Quality       # strong, pass, indeterminate, fail, fumble
Difficulty = Quality    # impossible, hard, ave, easy, v_easy

class HasStats(HasFungibleAssets[StatDomain], EntityMixin):
    stats: Counter[StatDomain]  # alias to wallet

class StatChallenge(HasConditions, Entity):
    cost: Counter[ FungibleAsset | StatDomain ]
    stat_domain: StatDomain
    difficulty: Difficulty
    payout: Counter[ FungibleAsset | StatDomain ]

    def taskee_can_pay_cost(self, taskee: HasStats, **modifiers): ...
    def taskee_pay_cost(self, taskee: HasStats, **modifiers): ...
    def taskee_can_receive_payout(self, taskee: HasStats, outcome: Outcome, **modifiers): ...
    def taskee_receive_payout(self, taskee: HasStats, outcome: Outcome, **modifiers): ...
    def get_taskee_challenge_result(self, taskee: HasStats, **modifiers) -> Outcome: ...

class StatChallengeHandler(TradeManager):
    ...

class ChallengeModifier(DynamicAsset):
    # "situational effect", dynamic asset owned by either the taskee or challenge
    # ? how do we apply more complicated effects like changing domain or pay with health instead of mana?
    applies_to: Criteria

    cost_modifier: QualityDelta
    payout_modifier: QualityDelta
    stat_domain_modifier: Any  # figure out type
    difficulty_modifier: QualityDelta

    def check_applies_to(self, has_stats: HasStats) -> bool: ...
    def apply_to(self, has_stats: HasStats): ...

class StatChallengeBlock(Block):
    challenge: StatChallenge


# todo: Other story node mechanics: look, outfit, personal names, credentials
