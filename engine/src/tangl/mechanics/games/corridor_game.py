"""
Shared-threshold corridor contest.

This kernel models a contested push-your-luck loop with one public threshold,
one scalar score per side, and a shared ordered source of advances.
"""
from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment

from .enums import GameResult, RoundResult
from .game import Game
from .handler import GameHandler


class CorridorMove(Enum):
    """Player actions in a scalar corridor contest."""

    ADVANCE = "advance"
    HOLD = "hold"


class CorridorGame(Game[CorridorMove]):
    """State for a contested shared-threshold corridor."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = None

    shared_target: int = 22
    source_sequence: list[int] = Field(default_factory=list)
    initial_player_has_initiative: bool = True
    starting_player_score: int = 0
    starting_opponent_score: int = 0

    source_index: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    player_score_value: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    opponent_score_value: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    player_has_initiative: bool = Field(
        default=True,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    def next_source_value(self) -> int | None:
        if self.source_index >= len(self.source_sequence):
            return None
        return self.source_sequence[self.source_index]

    def draw_next_value(self) -> int:
        value = self.source_sequence[self.source_index]
        self.source_index += 1
        return value

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "corridor_target": self.shared_target,
                "corridor_player_score": self.player_score_value,
                "corridor_opponent_score": self.opponent_score_value,
                "corridor_player_has_initiative": self.player_has_initiative,
                "corridor_next_value": self.next_source_value(),
                "corridor_source_index": self.source_index,
            }
        )
        return namespace


class CorridorGameHandler(GameHandler[CorridorGame]):
    """Handler for the scalar corridor contest."""

    game_cls: ClassVar[type[Game]] = CorridorGame

    def on_setup(self, game: CorridorGame) -> None:
        game.player_score_value = game.starting_player_score
        game.opponent_score_value = game.starting_opponent_score
        game.player_has_initiative = game.initial_player_has_initiative
        game.round_detail = {
            "outcome": "opening",
            "player_score": game.player_score_value,
            "opponent_score": game.opponent_score_value,
        }

    def get_available_moves(self, game: CorridorGame) -> list[CorridorMove]:
        return [CorridorMove.ADVANCE, CorridorMove.HOLD]

    def get_move_label(self, game: CorridorGame, move: CorridorMove) -> str:
        return "Advance" if move is CorridorMove.ADVANCE else "Hold"

    def resolve_round(
        self,
        game: CorridorGame,
        player_move: CorridorMove,
        opponent_move: CorridorMove | None,
    ) -> RoundResult:
        detail: dict[str, object] = {
            "initiative_before": game.player_has_initiative,
            "player_move": player_move.value,
        }

        actors = ["player", "opponent"] if game.player_has_initiative else ["opponent", "player"]
        moves = {
            "player": player_move,
            "opponent": opponent_move or self._choose_opponent_move(game),
        }
        detail["opponent_move"] = moves["opponent"].value

        for actor in actors:
            result = self._apply_turn(game, actor=actor, move=moves[actor], detail=detail)
            if result != RoundResult.CONTINUE:
                game.round_detail = detail
                return result

        game.player_has_initiative = not game.player_has_initiative
        detail["initiative_after"] = game.player_has_initiative
        detail["outcome"] = "continue"
        game.round_detail = detail
        return RoundResult.CONTINUE

    def evaluate(self, game: CorridorGame) -> GameResult:
        if game.score["player"] > 0:
            return GameResult.WIN
        if game.score["opponent"] > 0:
            return GameResult.LOSE
        return GameResult.IN_PROCESS

    def build_round_notes(
        self,
        game: CorridorGame,
        player_move: CorridorMove,
        opponent_move: CorridorMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["player_score"] = game.player_score_value
        detail["opponent_score"] = game.opponent_score_value
        detail["next_value"] = game.next_source_value()
        return detail

    def get_journal_fragments(self, game: CorridorGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        fragments = [
            ContentFragment(
                content=(
                    f"Scores settle at {notes.get('player_score', game.player_score_value)} "
                    f"to {notes.get('opponent_score', game.opponent_score_value)} "
                    f"against the shared target {game.shared_target}."
                )
            )
        ]
        if "player_draw" in notes:
            fragments.append(ContentFragment(content=f"You advance by {notes['player_draw']}."))
        if "opponent_draw" in notes:
            fragments.append(ContentFragment(content=f"Your rival advances by {notes['opponent_draw']}."))
        if last_round.result == RoundResult.WIN:
            fragments.append(ContentFragment(content="You close the corridor around your rival."))
        elif last_round.result == RoundResult.LOSE:
            fragments.append(ContentFragment(content="The corridor folds inward around you."))
        return fragments

    def _apply_turn(
        self,
        game: CorridorGame,
        *,
        actor: str,
        move: CorridorMove,
        detail: dict[str, object],
    ) -> RoundResult:
        if actor == "player":
            own_attr = "player_score_value"
            other_attr = "opponent_score_value"
        else:
            own_attr = "opponent_score_value"
            other_attr = "player_score_value"

        own_score = getattr(game, own_attr)
        other_score = getattr(game, other_attr)

        if move is CorridorMove.ADVANCE and game.next_source_value() is not None:
            drawn = game.draw_next_value()
            own_score += drawn
            setattr(game, own_attr, own_score)
            detail[f"{actor}_draw"] = drawn

        if own_score >= game.shared_target:
            if actor == "player":
                game.score["opponent"] = 1
                detail["outcome"] = "player_bust"
                return RoundResult.LOSE
            game.score["player"] = 1
            detail["outcome"] = "opponent_bust"
            return RoundResult.WIN

        if own_score < other_score < game.shared_target:
            if actor == "player":
                game.score["player"] = 1
                detail["outcome"] = "player_trap"
                return RoundResult.WIN
            game.score["opponent"] = 1
            detail["outcome"] = "opponent_trap"
            return RoundResult.LOSE

        detail[f"{actor}_move"] = move.value
        return RoundResult.CONTINUE

    def _choose_opponent_move(self, game: CorridorGame) -> CorridorMove:
        if game.opponent_score_value < game.player_score_value < game.shared_target:
            return CorridorMove.HOLD
        next_value = game.next_source_value()
        if next_value is None:
            return CorridorMove.HOLD
        if game.opponent_score_value + next_value >= game.shared_target:
            return CorridorMove.HOLD
        return CorridorMove.ADVANCE


class TwentyTwoGame(CorridorGame):
    """First concrete corridor skin inspired by the older TwentyTwo spike."""

    shared_target: int = 22
    source_sequence: list[int] = Field(default_factory=lambda: [4, 5, 3, 2, 6, 1, 4, 2])


class TwentyTwoGameHandler(CorridorGameHandler):
    """Concrete handler for the TwentyTwo skin."""

    game_cls: ClassVar[type[Game]] = TwentyTwoGame
