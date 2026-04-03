"""
Asymmetric challenge-response aggregate-force variant.

One side attacks with a posture and force profile. The defender answers with a
bounded commitment that can fail, meet, or beat that pressure. Meeting preserves
initiative for the attacker; beating flips initiative.
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment

from .aggregate_force_game import AggregateForceGame, AggregateForceGameHandler, ForceCommitMove
from .enums import GameResult, RoundResult
from .game import Game


class SiegeRpsGame(AggregateForceGame):
    """Asymmetric aggregate-force contest with explicit initiative."""

    force_types: list[str] = Field(default_factory=lambda: ["rock", "paper", "scissors"])
    force_beats: dict[str, str] = Field(
        default_factory=lambda: {
            "rock": "scissors",
            "paper": "rock",
            "scissors": "paper",
        }
    )
    force_weights: dict[str, int] = Field(
        default_factory=lambda: {
            "rock": 1,
            "paper": 1,
            "scissors": 1,
        }
    )
    player_opening_reserve: dict[str, int] = Field(
        default_factory=lambda: {
            "rock": 2,
            "paper": 1,
            "scissors": 1,
        }
    )
    opponent_opening_reserve: dict[str, int] = Field(
        default_factory=lambda: {
            "rock": 1,
            "paper": 2,
            "scissors": 1,
        }
    )
    player_has_initiative: bool = Field(
        default=True,
        json_schema_extra={"reset_field": True},
    )
    initial_player_has_initiative: bool = False
    initiative_bonus: float = 0.0
    response_pressure_tax: float = 0.0
    posture_pressure_bonus: dict[str, float] = Field(default_factory=dict)

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "siege_player_has_initiative": self.player_has_initiative,
                "siege_opponent_signal": (
                    self.opponent_next_move.as_dict()
                    if isinstance(self.opponent_next_move, ForceCommitMove)
                    else None
                ),
                "siege_initiative_bonus": self.initiative_bonus,
                "siege_response_pressure_tax": self.response_pressure_tax,
            }
        )
        return namespace


class SiegeRpsGameHandler(AggregateForceGameHandler[SiegeRpsGame]):
    """Challenge-response handler layered on the aggregate-force kernel."""

    game_cls: ClassVar[type[Game]] = SiegeRpsGame

    def on_setup(self, game: SiegeRpsGame) -> None:
        super().on_setup(game)
        game.player_has_initiative = game.initial_player_has_initiative

    def get_move_label(self, game: SiegeRpsGame, move: ForceCommitMove) -> str:
        prefix = "Attack with" if game.player_has_initiative else "Answer with"
        return f"{prefix} {self._format_profile(move.as_dict())}"

    def resolve_round(
        self,
        game: SiegeRpsGame,
        player_move: ForceCommitMove,
        opponent_move: ForceCommitMove | None,
    ) -> RoundResult:
        if opponent_move is None:
            raise RuntimeError("Siege RPS requires an opponent commitment")

        player_profile = player_move.as_dict()
        opponent_profile = opponent_move.as_dict()
        initiative_before = game.player_has_initiative

        if initiative_before:
            attacker_profile = player_profile
            defender_profile = opponent_profile
        else:
            attacker_profile = opponent_profile
            defender_profile = player_profile

        attack_pressure = self._pressure_value(
            game,
            attacker_profile,
            defender_profile,
            acting_as_attacker=True,
        )
        defense_pressure = self._pressure_value(
            game,
            defender_profile,
            attacker_profile,
            acting_as_attacker=False,
        ) - game.response_pressure_tax

        attacker_losses = self._allocate_casualties(game, defender_profile, attacker_profile)
        defender_losses = self._allocate_casualties(game, attacker_profile, defender_profile)

        if initiative_before:
            player_losses = attacker_losses
            opponent_losses = defender_losses
        else:
            player_losses = defender_losses
            opponent_losses = attacker_losses

        self._apply_losses(game.player_reserve, player_losses)
        self._apply_losses(game.opponent_reserve, opponent_losses)

        player_damage = self._weighted_total(game, opponent_losses)
        opponent_damage = self._weighted_total(game, player_losses)
        game.score["player"] += player_damage
        game.score["opponent"] += opponent_damage

        initiative_after = initiative_before
        if defense_pressure > attack_pressure:
            initiative_after = not initiative_before
        game.player_has_initiative = initiative_after

        detail = {
            "initiative_before": initiative_before,
            "initiative_after": initiative_after,
            "player_commit": player_profile,
            "opponent_commit": opponent_profile,
            "attack_pressure": attack_pressure,
            "defense_pressure": defense_pressure,
            "player_losses": player_losses,
            "opponent_losses": opponent_losses,
            "player_reserve": dict(game.player_reserve),
            "opponent_reserve": dict(game.opponent_reserve),
            "player_damage": player_damage,
            "opponent_damage": opponent_damage,
        }

        if initiative_before:
            if defense_pressure > attack_pressure:
                detail["outcome"] = "player_attack_beaten"
                game.round_detail = detail
                return RoundResult.LOSE
            if defense_pressure == attack_pressure:
                detail["outcome"] = "player_attack_met"
                game.round_detail = detail
                return RoundResult.DRAW
            detail["outcome"] = "player_attack_breaks_through"
            game.round_detail = detail
            return RoundResult.WIN

        if defense_pressure > attack_pressure:
            detail["outcome"] = "player_defense_beats_attack"
            game.round_detail = detail
            return RoundResult.WIN
        if defense_pressure == attack_pressure:
            detail["outcome"] = "player_defense_meets_attack"
            game.round_detail = detail
            return RoundResult.DRAW
        detail["outcome"] = "player_defense_fails"
        game.round_detail = detail
        return RoundResult.LOSE

    def get_journal_fragments(self, game: SiegeRpsGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        role = "attacker" if notes.get("initiative_before") else "defender"
        next_role = "attacker" if notes.get("initiative_after") else "defender"
        return [
            ContentFragment(
                content=(
                    f"You enter as {role}, committing "
                    f"{self._format_profile(notes.get('player_commit', {}))}."
                )
            ),
            ContentFragment(
                content=(
                    f"Pressure resolves at {notes.get('attack_pressure', 0):.2f} "
                    f"versus {notes.get('defense_pressure', 0):.2f}."
                )
            ),
            ContentFragment(content=f"Initiative now belongs to the {next_role}."),
        ]

    def evaluate(self, game: SiegeRpsGame) -> GameResult:
        player_force = game.total_force(game.player_reserve)
        opponent_force = game.total_force(game.opponent_reserve)

        if player_force <= 0 and opponent_force <= 0:
            if game.score["player"] > game.score["opponent"]:
                return GameResult.WIN
            if game.score["player"] < game.score["opponent"]:
                return GameResult.LOSE
            return GameResult.DRAW
        if opponent_force <= 0:
            return GameResult.WIN
        if player_force <= 0:
            return GameResult.LOSE
        return GameResult.IN_PROCESS

    def _preselect_opponent_move(self, game: SiegeRpsGame) -> None:
        if game.player_has_initiative:
            game.opponent_next_move = None
            return
        game.opponent_next_move = self._choose_attack_profile(game)

    def _finalize_opponent_move(
        self,
        game: SiegeRpsGame,
        player_move: ForceCommitMove,
    ) -> ForceCommitMove | None:
        if game.player_has_initiative:
            return self._choose_response_profile(game, player_move.as_dict())
        return game.opponent_next_move

    def _choose_attack_profile(self, game: SiegeRpsGame) -> ForceCommitMove | None:
        moves = self._profiles_for_reserve(game, game.opponent_reserve)
        if not moves:
            return None
        return max(moves, key=lambda move: (move.total_units, len(move.profile)))

    def _choose_response_profile(
        self,
        game: SiegeRpsGame,
        attacker_profile: dict[str, int],
    ) -> ForceCommitMove | None:
        moves = self._profiles_for_reserve(game, game.opponent_reserve)
        if not moves:
            return None
        attack_pressure = self._pressure_value(
            game,
            attacker_profile,
            {},
            acting_as_attacker=True,
        )
        ranked = sorted(
            moves,
            key=lambda move: (
                self._pressure_value(
                    game,
                    move.as_dict(),
                    attacker_profile,
                    acting_as_attacker=False,
                ) - game.response_pressure_tax,
                move.total_units,
            ),
        )
        for move in ranked:
            defense_pressure = self._pressure_value(
                game,
                move.as_dict(),
                attacker_profile,
                acting_as_attacker=False,
            ) - game.response_pressure_tax
            if defense_pressure >= attack_pressure:
                return move
        return ranked[-1]

    def _pressure_value(
        self,
        game: SiegeRpsGame,
        actor: dict[str, int],
        opposing: dict[str, int],
        *,
        acting_as_attacker: bool,
    ) -> float:
        opposing_types = {label for label, count in opposing.items() if count > 0}
        if not actor:
            return 0.0

        favorable = 0.0
        neutral = 0.0
        disadvantaged = 0.0
        bonus = 0.0
        for label, count in actor.items():
            if count <= 0:
                continue
            power = float(count * game.get_force_weight(label))
            bonus += count * game.posture_pressure_bonus.get(label, 0.0)
            beaten = game.force_beats.get(label)
            if beaten in opposing_types:
                favorable += power
            elif label in opposing_types:
                neutral += power
            else:
                disadvantaged += power

        pressure = favorable + neutral + (disadvantaged / max(game.disadvantaged_trade_ratio, 1))
        pressure += bonus
        if acting_as_attacker:
            pressure += game.initiative_bonus
        return pressure
