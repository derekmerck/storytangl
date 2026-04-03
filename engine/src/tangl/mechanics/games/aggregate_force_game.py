"""
Aggregate-force contest kernel.

This family lifts atomic move contests into reserve-and-composition contests.
Each round, both sides commit a bounded profile from reserve, inflict typed
attrition based on composition, and return surviving force to reserve.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import ClassVar, TypeVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment

from .enums import GameResult, RoundResult
from .game import Game
from .handler import GameHandler


ForceProfile = tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class ForceCommitMove:
    """Structured commitment profile for aggregate-force contests."""

    profile: ForceProfile

    def as_dict(self) -> dict[str, int]:
        """Return the commitment profile as a mutable mapping."""

        return {label: count for label, count in self.profile}

    @property
    def total_units(self) -> int:
        """Return the committed unit count."""

        return sum(count for _, count in self.profile)


class AggregateForceGame(Game[ForceCommitMove]):
    """Shared state for reserve-based aggregate-force contests."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = "aggregate_force_greedy"

    force_types: list[str] = Field(default_factory=list)
    force_beats: dict[str, str] = Field(default_factory=dict)
    force_weights: dict[str, int] = Field(default_factory=dict)

    max_commit_size: int = 3
    max_mix_types: int = 2
    disadvantaged_trade_ratio: int = 2

    player_opening_reserve: dict[str, int] = Field(default_factory=dict)
    opponent_opening_reserve: dict[str, int] = Field(default_factory=dict)

    player_reserve: dict[str, int] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    opponent_reserve: dict[str, int] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    def ordered_force_types(self) -> list[str]:
        """Return the stable type ordering for profiles and labels."""

        if self.force_types:
            return list(self.force_types)
        return list(self.force_beats)

    def get_force_weight(self, label: str) -> int:
        """Return the force weight for a given type."""

        return self.force_weights.get(label, 1)

    def total_force(self, reserve: dict[str, int]) -> int:
        """Return weighted force remaining in a reserve."""

        return sum(count * self.get_force_weight(label) for label, count in reserve.items())

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "aggregate_force_types": self.ordered_force_types(),
                "aggregate_player_reserve": dict(self.player_reserve),
                "aggregate_opponent_reserve": dict(self.opponent_reserve),
                "aggregate_player_force": self.total_force(self.player_reserve),
                "aggregate_opponent_force": self.total_force(self.opponent_reserve),
                "aggregate_max_commit_size": self.max_commit_size,
                "aggregate_max_mix_types": self.max_mix_types,
                "aggregate_force_weights": dict(self.force_weights),
            }
        )
        return namespace


AggregateForceGameT = TypeVar("AggregateForceGameT", bound=AggregateForceGame)


class AggregateForceGameHandler(GameHandler[AggregateForceGameT]):
    """Shared handler for reserve-and-composition contests."""

    game_cls: ClassVar[type[Game]] = AggregateForceGame

    def on_setup(self, game: AggregateForceGameT) -> None:
        game.player_reserve = dict(game.player_opening_reserve)
        game.opponent_reserve = dict(game.opponent_opening_reserve)
        game.round_detail = {
            "outcome": "opening",
            "player_reserve": dict(game.player_reserve),
            "opponent_reserve": dict(game.opponent_reserve),
        }

    def get_available_moves(self, game: AggregateForceGameT) -> list[ForceCommitMove]:
        return self._profiles_for_reserve(game, game.player_reserve)

    def get_move_label(self, game: AggregateForceGameT, move: ForceCommitMove) -> str:
        return f"Commit {self._format_profile(move.as_dict())}"

    def resolve_round(
        self,
        game: AggregateForceGameT,
        player_move: ForceCommitMove,
        opponent_move: ForceCommitMove | None,
    ) -> RoundResult:
        player_commit = player_move.as_dict()
        opponent_commit = (
            opponent_move.as_dict()
            if isinstance(opponent_move, ForceCommitMove)
            else {}
        )
        if not opponent_commit:
            opponent_profiles = self._profiles_for_reserve(game, game.opponent_reserve)
            if opponent_profiles:
                opponent_commit = opponent_profiles[0].as_dict()

        player_losses = self._allocate_casualties(game, opponent_commit, player_commit)
        opponent_losses = self._allocate_casualties(game, player_commit, opponent_commit)

        self._apply_losses(game.player_reserve, player_losses)
        self._apply_losses(game.opponent_reserve, opponent_losses)

        player_damage = self._weighted_total(game, opponent_losses)
        opponent_damage = self._weighted_total(game, player_losses)
        game.score["player"] += player_damage
        game.score["opponent"] += opponent_damage

        detail = {
            "player_commit": player_commit,
            "opponent_commit": opponent_commit,
            "player_losses": player_losses,
            "opponent_losses": opponent_losses,
            "player_reserve": dict(game.player_reserve),
            "opponent_reserve": dict(game.opponent_reserve),
            "player_damage": player_damage,
            "opponent_damage": opponent_damage,
        }

        if player_damage > opponent_damage:
            detail["outcome"] = "win"
            game.round_detail = detail
            return RoundResult.WIN
        if player_damage < opponent_damage:
            detail["outcome"] = "lose"
            game.round_detail = detail
            return RoundResult.LOSE

        detail["outcome"] = "draw"
        game.round_detail = detail
        return RoundResult.DRAW

    def evaluate(self, game: AggregateForceGameT) -> GameResult:
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

    def build_round_notes(
        self,
        game: AggregateForceGameT,
        player_move: ForceCommitMove,
        opponent_move: ForceCommitMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["opponent_next_move"] = (
            self._serialize_move(opponent_move)
            if opponent_move is not None
            else self._serialize_move(game.opponent_next_move)
        )
        return detail

    def get_journal_fragments(self, game: AggregateForceGameT) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        fragments = [
            ContentFragment(
                content=(
                    f"You commit {self._format_profile(notes.get('player_commit', {}))}. "
                    f"Your opponent commits {self._format_profile(notes.get('opponent_commit', {}))}."
                )
            ),
            ContentFragment(
                content=(
                    f"You inflict {notes.get('player_damage', 0)} attrition and suffer "
                    f"{notes.get('opponent_damage', 0)}."
                )
            ),
            ContentFragment(
                content=(
                    f"Reserve now stands at "
                    f"{self._format_profile(notes.get('player_reserve', {}))} versus "
                    f"{self._format_profile(notes.get('opponent_reserve', {}))}."
                )
            ),
        ]
        return fragments

    def _profiles_for_reserve(
        self,
        game: AggregateForceGameT,
        reserve: dict[str, int],
    ) -> list[ForceCommitMove]:
        types = [label for label in game.ordered_force_types() if reserve.get(label, 0) > 0]
        if not types:
            return []

        count_ranges = [range(reserve[label] + 1) for label in types]
        profiles: set[ForceProfile] = set()
        for counts in product(*count_ranges):
            total = sum(counts)
            mix = sum(1 for count in counts if count > 0)
            if total <= 0 or total > game.max_commit_size or mix > game.max_mix_types:
                continue
            profile = tuple(
                (label, count)
                for label, count in zip(types, counts, strict=True)
                if count > 0
            )
            profiles.add(profile)

        return [ForceCommitMove(profile=profile) for profile in sorted(profiles)]

    def _allocate_casualties(
        self,
        game: AggregateForceGameT,
        attacker: dict[str, int],
        defender: dict[str, int],
    ) -> dict[str, int]:
        budget = self._casualty_budget(game, attacker, defender)
        if budget <= 0:
            return {}

        priorities = self._defender_target_priority(game, attacker, defender)
        losses: dict[str, int] = {}
        remaining = budget
        for label in priorities:
            available = defender.get(label, 0)
            if available <= 0 or remaining <= 0:
                continue
            taken = min(available, remaining)
            losses[label] = taken
            remaining -= taken
        return losses

    def _casualty_budget(
        self,
        game: AggregateForceGameT,
        attacker: dict[str, int],
        defender: dict[str, int],
    ) -> int:
        if not attacker or not defender:
            return 0

        defender_types = {label for label, count in defender.items() if count > 0}
        favorable = 0
        neutral = 0
        disadvantaged = 0

        for label, count in attacker.items():
            if count <= 0:
                continue
            power = count * game.get_force_weight(label)
            beaten = game.force_beats.get(label)
            if beaten in defender_types:
                favorable += power
            elif label in defender_types:
                neutral += power
            else:
                disadvantaged += power

        budget = favorable + neutral + (disadvantaged // max(game.disadvantaged_trade_ratio, 1))
        return min(budget, sum(defender.values()))

    def _defender_target_priority(
        self,
        game: AggregateForceGameT,
        attacker: dict[str, int],
        defender: dict[str, int],
    ) -> list[str]:
        attacker_types = {label for label, count in attacker.items() if count > 0}

        def priority(label: str) -> tuple[int, int]:
            if any(game.force_beats.get(attacker_label) == label for attacker_label in attacker_types):
                return (0, game.ordered_force_types().index(label))
            if label in attacker_types:
                return (1, game.ordered_force_types().index(label))
            return (2, game.ordered_force_types().index(label))

        return sorted((label for label, count in defender.items() if count > 0), key=priority)

    def _apply_losses(self, reserve: dict[str, int], losses: dict[str, int]) -> None:
        for label, count in losses.items():
            reserve[label] = max(reserve.get(label, 0) - count, 0)

    def _weighted_total(self, game: AggregateForceGameT, profile: dict[str, int]) -> int:
        return sum(count * game.get_force_weight(label) for label, count in profile.items())

    def _format_profile(self, profile: dict[str, int]) -> str:
        if not profile:
            return "nothing"
        parts = [f"{count} {label}" for label, count in profile.items() if count > 0]
        return " + ".join(parts)

    def _serialize_move(self, move: ForceCommitMove | None) -> dict[str, int] | None:
        if move is None:
            return None
        return move.as_dict()
