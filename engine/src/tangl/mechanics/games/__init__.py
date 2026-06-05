"""
Game mechanics core - pure domain logic.

This package provides the foundational game state machine with no VM dependencies.
It can be tested in isolation and bolted onto the VM phase bus later.

Core Classes
------------
Game : BaseModel
    Stateful game instance container.
GameHandler : ABC
    Stateless rules engine that operates on Game instances.
RoundRecord : dataclass
    Immutable record of a single round's outcome.

Enums
-----
GamePhase : Enum
    Lifecycle phase (PENDING, READY, RESOLVING, TERMINAL).
GameResult : Enum
    Game outcome (IN_PROCESS, WIN, LOSE, DRAW).
RoundResult : Enum
    Per-round outcome (WIN, LOSE, DRAW, CONTINUE).

Registries
----------
opponent_strategies : StrategyRegistry
    Named strategies for opponent move selection.
scoring_strategies : StrategyRegistry
    Named strategies for terminal condition evaluation.

Example
-------
>>> from game_core import Game, GameHandler, GamePhase, GameResult
>>> 
>>> class MyGame(Game):
...     pass
>>> 
>>> class MyHandler(GameHandler[MyGame]):
...     def get_available_moves(self, game):
...         return ["move_a", "move_b"]
...     
...     def resolve_round(self, game, player_move, opponent_move):
...         # ... game logic ...
...         return RoundResult.WIN
>>> 
>>> game = MyGame()
>>> handler = MyHandler()
>>> handler.setup(game)
>>> handler.receive_move(game, "move_a")
"""
"""
Game mechanics integration with the story VM.

This package bridges Layer 2 game core (:mod:`tangl.mechanics.games`) with
Layer 3 narrative traversal. Use :class:`HasGame` to attach a game instance
and handler to a node.
"""

from .enums import GamePhase, GameResult, RoundResult
from .game import Game, RoundRecord, Move
from .handler import GameHandler, SimpleGameHandler
from .strategies import (
    StrategyRegistry,
    opponent_strategies,
    scoring_strategies,
)

from .has_game import HasGame
from .handlers import (
    generate_game_journal,
    inject_game_context,
    process_game_move,
    provision_game_moves,
    setup_game_on_first_visit,
)
from .blackjack_game import BlackjackGame, BlackjackGameHandler, BlackjackMove, PlayingCard
from .nim_game import NimGame, NimGameHandler
from .aggregate_force_game import (
    AggregateForceGame,
    AggregateForceGameHandler,
    ForceCommitMove,
)
from .bag_rps_game import BagRpsGame, BagRpsGameHandler
from .incremental_game import (
    BuildSpec,
    IncrementalGame,
    IncrementalGameHandler,
    IncrementalMove,
    PromotionSpec,
    TaskSpec,
)
from .corridor_game import CorridorGame, CorridorGameHandler, CorridorMove, TwentyTwoGame, TwentyTwoGameHandler
from .siege_rps_game import SiegeRpsGame, SiegeRpsGameHandler
from .picking_game import PickingGame, PickingGameHandler, PickingMove
from .kim_game import KimGame, KimGameHandler, KimMove
from .credentials_enums import (
    ContrabandItem,
    CredentialStatus,
    CredentialToken,
    DEFAULT_RESTRICTIONS,
    FailureClass,
    FailureMode,
    Indication,
    Region,
    RestrictionLevel,
    RestrictionMap,
    RestrictionRule,
    Restrictions,
)
from .credentials_game import (
    CredentialCase,
    CredentialCaseResult,
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
    CredentialsMove,
    derive_disposition,
    disposition_penalty,
    DISPOSITION_PENALTY,
)
from .credentials_factory import (
    applicable_modes,
    apply_failure,
    build_valid,
    degrade,
    make_case,
    render_narrative,
    sample_failure_mode,
)
from .credentials_roster import (
    ScenarioOffer,
    ShiftSpec,
    generate_roster,
    make_offer,
    materialize,
)


__all__ = [
    # Enums
    "GamePhase",
    "GameResult", 
    "RoundResult",
    # Core classes
    "Game",
    "RoundRecord",
    "Move",
    "GameHandler",
    "SimpleGameHandler",
    # Registries
    "StrategyRegistry",
    "opponent_strategies",
    "scoring_strategies",
    # Reference games
    "BlackjackGame",
    "BlackjackGameHandler",
    "BlackjackMove",
    "PlayingCard",
    "NimGame",
    "NimGameHandler",
    "AggregateForceGame",
    "AggregateForceGameHandler",
    "ForceCommitMove",
    "BagRpsGame",
    "BagRpsGameHandler",
    "TaskSpec",
    "BuildSpec",
    "PromotionSpec",
    "IncrementalGame",
    "IncrementalGameHandler",
    "IncrementalMove",
    "CorridorGame",
    "CorridorGameHandler",
    "CorridorMove",
    "TwentyTwoGame",
    "TwentyTwoGameHandler",
    "SiegeRpsGame",
    "SiegeRpsGameHandler",
    "PickingGame",
    "PickingGameHandler",
    "PickingMove",
    "KimGame",
    "KimGameHandler",
    "KimMove",
    "CredentialsGame",
    "CredentialsGameHandler",
    "CredentialsMove",
    "CredentialDisposition",
    "CredentialCase",
    "CredentialCaseResult",
    "derive_disposition",
    "ContrabandItem",
    "CredentialStatus",
    "CredentialToken",
    "Indication",
    "Region",
    "RestrictionLevel",
    "RestrictionMap",
    "RestrictionRule",
    "Restrictions",
    "DEFAULT_RESTRICTIONS",
    "FailureClass",
    "FailureMode",
    "build_valid",
    "degrade",
    "make_case",
    "render_narrative",
    "apply_failure",
    "applicable_modes",
    "sample_failure_mode",
    "ScenarioOffer",
    "ShiftSpec",
    "generate_roster",
    "make_offer",
    "materialize",
    # Dispatch
    "HasGame",
    "generate_game_journal",
    "inject_game_context",
    "process_game_move",
    "provision_game_moves",
    "setup_game_on_first_visit",

]
