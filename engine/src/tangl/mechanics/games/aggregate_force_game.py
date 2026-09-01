"""
Aggregate-force contest kernel.

This family lifts atomic move contests into reserve-and-composition contests.
Each round, both sides commit a bounded profile from reserve, inflict typed
attrition based on composition, and return surviving force to reserve.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import ClassVar, TypeVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment
from tangl.story.concepts.asset import AssetWallet

from tangl.vm.ctx import VmPhaseCtx

from .enums import GameResult, RoundResult
from .game import Game
from .game_token import (
    GameTokenSpec,
    affiliation_of,
    dominant_affiliation,
    transfer_tokens,
    weight_of,
)
from .handler import GameHandler


ForceProfile = tuple[tuple[str, int], ...]


class ForceDisposition(str, Enum):
    """Where a token goes once a clash resolves.

    Commitment is a real transfer from reserve into an active pool, so every
    committed token must be routed somewhere afterwards.
    """

    #: Stays active, still committed for the next round.
    CONSERVE = "conserve"
    #: Returns to its owner's reserve.
    RETIRE = "retire"
    #: Leaves the game entirely.
    DECIMATE = "decimate"
    #: Passes to the opponent's reserve.
    CEDE = "cede"


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

    #: Dominance cycle between **affiliations**. When a contest declares no
    #: token specs each label is its own affiliation, so this keeps the plain
    #: one-token-per-colour shape unchanged.
    force_beats: dict[str, str] = Field(default_factory=dict)

    #: Per-token colour and weight. Declaring several labels with the same
    #: affiliation and different values is what gives a bag *sizes* of a type —
    #: a heavy brute and a light brute both answer to "rock".
    token_specs: dict[str, GameTokenSpec] = Field(default_factory=dict)

    #: Legacy-free weight fallback for contests that declare no token specs.
    force_weights: dict[str, int] = Field(default_factory=dict)

    max_commit_size: int = 3
    max_mix_types: int = 2
    disadvantaged_trade_ratio: int = 2

    player_opening_reserve: dict[str, int] = Field(default_factory=dict)
    opponent_opening_reserve: dict[str, int] = Field(default_factory=dict)

    #: What happens to tokens that survive a clash. Retiring them is the
    #: classic sortie; conserving them builds a standing front line.
    survivor_disposition: ForceDisposition = ForceDisposition.RETIRE

    player_reserve: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"reset_field": True},
    )
    opponent_reserve: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"reset_field": True},
    )
    player_active: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"reset_field": True},
    )
    opponent_active: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"reset_field": True},
    )
    player_eliminated: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"reset_field": True},
    )
    opponent_eliminated: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    def reserve_of(self, owner: str) -> AssetWallet:
        """Return one side's reserve bag."""

        return self.player_reserve if owner == "player" else self.opponent_reserve

    def active_of(self, owner: str) -> AssetWallet:
        """Return one side's committed, in-play pool."""

        return self.player_active if owner == "player" else self.opponent_active

    def eliminated_of(self, owner: str) -> AssetWallet:
        """Return one side's out-of-game pile."""

        return self.player_eliminated if owner == "player" else self.opponent_eliminated

    def standing_force(self, owner: str) -> int:
        """Return weighted force still available: reserve plus what is in play.

        A side is not beaten merely because everything it owns is committed.
        """

        return self.total_force(self.reserve_of(owner)) + self.total_force(
            self.active_of(owner)
        )

    def rank_ladder(self, affiliation: str) -> list[str]:
        """Return one affiliation's token labels ordered light to heavy.

        Weight classes within a colour are a ladder: ``blue+0`` below
        ``blue+1``. Promotion and demotion walk it, so a field brevet, reserve
        training, an injury, or illness changes what a token *is* without
        changing whose it is or where it sits.
        """

        definitions = self.token_definitions()
        labels = [
            label
            for label in self.ordered_force_types()
            if affiliation_of(label, definitions) == affiliation
        ]
        return sorted(labels, key=lambda label: (weight_of(label, definitions), label))

    def ranked_neighbor(self, label: str, steps: int) -> str | None:
        """Return the label ``steps`` rungs up or down its own weight ladder.

        Returns None at the ends of the ladder, so a promotion with nowhere to
        go is a no-op rather than an error.
        """

        ladder = self.rank_ladder(self.get_force_affiliation(label))
        if label not in ladder:
            return None
        target = ladder.index(label) + steps
        if target < 0 or target >= len(ladder):
            return None
        return ladder[target]

    def ordered_force_types(self) -> list[str]:
        """Return the stable *token label* ordering for profiles and labels."""

        if self.force_types:
            return list(self.force_types)
        if self.token_specs:
            return list(self.token_specs)
        return list(self.force_beats)

    def token_definitions(self) -> dict[str, GameTokenSpec]:
        """Return the resolved token vocabulary, filling weights from fallback."""

        definitions = dict(self.token_specs)
        for label, weight in self.force_weights.items():
            if label not in definitions:
                definitions[label] = GameTokenSpec(value=weight)
        return definitions

    def get_force_affiliation(self, label: str) -> str:
        """Return the dominance class a token label belongs to."""

        return affiliation_of(label, self.token_definitions())

    def get_force_weight(self, label: str) -> int:
        """Return the force weight for a given token label."""

        return int(weight_of(label, self.token_definitions()))

    def affiliations_present(self, reserve) -> set[str]:
        """Return the affiliations represented in a reserve or profile."""

        return {
            self.get_force_affiliation(label)
            for label, count in reserve.items()
            if count > 0
        }

    def dominant_affiliation(self, reserve) -> str | None:
        """Return the affiliation carrying the most weight in a holding."""

        return dominant_affiliation(reserve, self.token_definitions())

    def total_force(self, reserve) -> int:
        """Return weighted force remaining in a reserve."""

        return sum(count * self.get_force_weight(label) for label, count in reserve.items())

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "aggregate_force_types": self.ordered_force_types(),
                "aggregate_player_reserve": dict(self.player_reserve.amounts),
                "aggregate_opponent_reserve": dict(self.opponent_reserve.amounts),
                "aggregate_player_dominant": self.dominant_affiliation(self.player_reserve),
                "aggregate_opponent_dominant": self.dominant_affiliation(self.opponent_reserve),
                "aggregate_player_active": dict(self.player_active.amounts),
                "aggregate_opponent_active": dict(self.opponent_active.amounts),
                "aggregate_player_eliminated": dict(self.player_eliminated.amounts),
                "aggregate_opponent_eliminated": dict(self.opponent_eliminated.amounts),
                "aggregate_player_standing": self.standing_force("player"),
                "aggregate_opponent_standing": self.standing_force("opponent"),
                "aggregate_survivor_disposition": self.survivor_disposition.value,
                "aggregate_player_force": self.total_force(self.player_reserve),
                "aggregate_opponent_force": self.total_force(self.opponent_reserve),
                "aggregate_max_commit_size": self.max_commit_size,
                "aggregate_max_mix_types": self.max_mix_types,
                "aggregate_force_weights": {
                    label: self.get_force_weight(label)
                    for label in self.ordered_force_types()
                },
                "aggregate_force_affiliations": {
                    label: self.get_force_affiliation(label)
                    for label in self.ordered_force_types()
                },
            }
        )
        return namespace


AggregateForceGameT = TypeVar("AggregateForceGameT", bound=AggregateForceGame)


class AggregateForceGameHandler(GameHandler[AggregateForceGameT]):
    """Shared handler for reserve-and-composition contests."""

    game_cls: ClassVar[type[Game]] = AggregateForceGame

    def on_setup(self, game: AggregateForceGameT) -> None:
        game.player_reserve = AssetWallet()
        game.player_reserve.gain({
            label: count for label, count in game.player_opening_reserve.items() if count > 0
        })
        game.opponent_reserve = AssetWallet()
        game.opponent_reserve.gain({
            label: count for label, count in game.opponent_opening_reserve.items() if count > 0
        })
        game.round_detail = {
            "outcome": "opening",
            "player_reserve": dict(game.player_reserve.amounts),
            "opponent_reserve": dict(game.opponent_reserve.amounts),
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

        # Commitment is a real transfer: tokens leave the reserve and stand in
        # the active pool until the clash routes them somewhere.
        player_commit = self.commit_forces(game, "player", player_commit)
        opponent_commit = self.commit_forces(game, "opponent", opponent_commit)

        player_losses = self._allocate_casualties(
            game, game.opponent_active, game.player_active
        )
        opponent_losses = self._allocate_casualties(
            game, game.player_active, game.opponent_active
        )

        self.apply_casualties(game, "player", player_losses)
        self.apply_casualties(game, "opponent", opponent_losses)

        player_survivors = self.dispose_survivors(game, "player")
        opponent_survivors = self.dispose_survivors(game, "opponent")

        player_damage = self._weighted_total(game, opponent_losses)
        opponent_damage = self._weighted_total(game, player_losses)
        game.score["player"] += player_damage
        game.score["opponent"] += opponent_damage

        detail = {
            "player_commit": player_commit,
            "opponent_commit": opponent_commit,
            "player_losses": player_losses,
            "opponent_losses": opponent_losses,
            "player_dominant": game.dominant_affiliation(player_commit),
            "opponent_dominant": game.dominant_affiliation(opponent_commit),
            "player_survivors": player_survivors,
            "opponent_survivors": opponent_survivors,
            "player_active": dict(game.player_active.amounts),
            "opponent_active": dict(game.opponent_active.amounts),
            "player_eliminated": dict(game.player_eliminated.amounts),
            "opponent_eliminated": dict(game.opponent_eliminated.amounts),
            "survivor_disposition": game.survivor_disposition.value,
            "player_reserve": dict(game.player_reserve.amounts),
            "opponent_reserve": dict(game.opponent_reserve.amounts),
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
        player_force = game.standing_force("player")
        opponent_force = game.standing_force("opponent")

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

    def get_journal_fragments(
        self,
        game: AggregateForceGameT,
        *,
        ctx: VmPhaseCtx | None = None,
    ) -> list[ContentFragment] | None:
        _ = ctx
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

    # ─────────────────────────────────────────────────────────────────
    # The commitment cycle
    #
    # Reserve -> active on commit; active -> reserve, out of the game, or the
    # opponent's reserve on resolution. These are public because a world may
    # want to drive them for dramatic effect rather than only through a clash.
    # ─────────────────────────────────────────────────────────────────

    def commit_forces(
        self,
        game: AggregateForceGameT,
        owner: str,
        profile: dict[str, int],
    ) -> dict[str, int]:
        """Move a committed profile from reserve into the active pool."""

        return transfer_tokens(game.reserve_of(owner), game.active_of(owner), profile)

    def apply_casualties(
        self,
        game: AggregateForceGameT,
        owner: str,
        losses: dict[str, int],
    ) -> dict[str, int]:
        """Send casualties out of the active pool and out of the game."""

        return transfer_tokens(game.active_of(owner), game.eliminated_of(owner), losses)

    def dispose_survivors(
        self,
        game: AggregateForceGameT,
        owner: str,
        disposition: ForceDisposition | None = None,
    ) -> dict[str, int]:
        """Route whatever survived the clash out of the active pool.

        Returns what moved. ``CONSERVE`` moves nothing, leaving the pool
        standing for the next round.
        """

        chosen = disposition or game.survivor_disposition
        active = game.active_of(owner)
        survivors = {label: count for label, count in active.items() if count > 0}
        if not survivors or chosen is ForceDisposition.CONSERVE:
            return {}

        if chosen is ForceDisposition.RETIRE:
            destination = game.reserve_of(owner)
        elif chosen is ForceDisposition.DECIMATE:
            destination = game.eliminated_of(owner)
        else:  # CEDE
            rival = "opponent" if owner == "player" else "player"
            destination = game.reserve_of(rival)

        return transfer_tokens(active, destination, survivors)

    def adjust_reserve(
        self,
        game: AggregateForceGameT,
        owner: str,
        deltas: dict[str, int],
        *,
        reason: str | None = None,
    ) -> dict[str, object]:
        """Augment or hobble a reserve between clashes.

        This is the seam for events that happen away from the field — a surge
        of fresh recruits, a plague at home — so a world can move the economy
        of force without pretending the change came out of a fight.
        """

        reserve = game.reserve_of(owner)
        gained = {label: count for label, count in deltas.items() if count > 0}
        lost = {
            label: min(-count, reserve[label])
            for label, count in deltas.items()
            if count < 0
        }
        lost = {label: count for label, count in lost.items() if count > 0}

        if gained:
            reserve.gain(gained)
        if lost:
            transfer_tokens(reserve, game.eliminated_of(owner), lost)

        return {"owner": owner, "gained": gained, "lost": lost, "reason": reason}

    def _pool_of(self, game: AggregateForceGameT, owner: str, pool: str) -> AssetWallet:
        if pool == "active":
            return game.active_of(owner)
        if pool == "eliminated":
            return game.eliminated_of(owner)
        return game.reserve_of(owner)

    def transmute(
        self,
        game: AggregateForceGameT,
        owner: str,
        label: str,
        to_label: str,
        count: int = 1,
        *,
        pool: str = "reserve",
        to_owner: str | None = None,
        to_pool: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object] | None:
        """Change what tokens are, whose they are, or where they sit.

        A token's state has three independent axes, and this moves any of them
        at once:

        - **owner** — a token changes sides, which is a defection
        - **affiliation** — rock becomes paper, a metamorphosis
        - **weight** — a rung up or down its own ladder, amelioration or decay

        The returned record names whichever axes actually changed, so a world
        can narrate the difference between a bribe, a transformation, and a
        promotion without inspecting wallets itself. Returns None when there is
        nothing to move.
        """

        source = self._pool_of(game, owner, pool)
        destination = self._pool_of(game, to_owner or owner, to_pool or pool)
        moved = min(count, source[label])
        if moved <= 0:
            return None

        source.spend({label: moved})
        destination.gain({to_label: moved})

        changes: list[str] = []
        if to_owner is not None and to_owner != owner:
            changes.append("defect")
        if game.get_force_affiliation(label) != game.get_force_affiliation(to_label):
            changes.append("metamorphosis")
        before = game.get_force_weight(label)
        after = game.get_force_weight(to_label)
        if after > before:
            changes.append("ameliorate")
        elif after < before:
            changes.append("decay")

        return {
            "owner": owner,
            "to_owner": to_owner or owner,
            "pool": pool,
            "to_pool": to_pool or pool,
            "from": label,
            "to": to_label,
            "count": moved,
            "changes": changes,
            "reason": reason,
        }

    def retrain(
        self,
        game: AggregateForceGameT,
        owner: str,
        label: str,
        count: int = 1,
        *,
        steps: int = 1,
        pool: str = "reserve",
        reason: str | None = None,
    ) -> dict[str, object] | None:
        """Promote or demote tokens a rung on their own weight ladder.

        The weight-axis convenience over :meth:`transmute`: same side, same
        colour, different class. Positive ``steps`` promotes — a brevet,
        reserve training — and negative demotes, for a field injury or illness.
        Returns None when the ladder has no rung to move to.
        """

        target = game.ranked_neighbor(label, steps)
        if target is None:
            return None
        record = self.transmute(
            game, owner, label, target, count, pool=pool, reason=reason
        )
        if record is not None:
            record["direction"] = "promote" if steps > 0 else "demote"
        return record

    def _profiles_for_reserve(
        self,
        game: AggregateForceGameT,
        reserve: dict[str, int],
    ) -> list[ForceCommitMove]:
        types = [label for label in game.ordered_force_types() if reserve[label] > 0]
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
            available = defender[label] if hasattr(defender, "amounts") else defender.get(label, 0)
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

        defender_affiliations = game.affiliations_present(defender)
        favorable = 0
        neutral = 0
        disadvantaged = 0

        for label, count in attacker.items():
            if count <= 0:
                continue
            power = count * game.get_force_weight(label)
            affiliation = game.get_force_affiliation(label)
            beaten = game.force_beats.get(affiliation)
            if beaten in defender_affiliations:
                favorable += power
            elif affiliation in defender_affiliations:
                neutral += power
            else:
                disadvantaged += power

        budget = favorable + neutral + (disadvantaged // max(game.disadvantaged_trade_ratio, 1))
        return min(budget, sum(count for _, count in defender.items()))

    def _defender_target_priority(
        self,
        game: AggregateForceGameT,
        attacker: dict[str, int],
        defender: dict[str, int],
    ) -> list[str]:
        attacker_affiliations = game.affiliations_present(attacker)
        order = game.ordered_force_types()

        def priority(label: str) -> tuple[int, int]:
            affiliation = game.get_force_affiliation(label)
            rank = order.index(label) if label in order else len(order)
            if any(game.force_beats.get(attacking) == affiliation for attacking in attacker_affiliations):
                return (0, rank)
            if affiliation in attacker_affiliations:
                return (1, rank)
            return (2, rank)

        return sorted((label for label, count in defender.items() if count > 0), key=priority)

    def _apply_losses(self, reserve: AssetWallet, losses: dict[str, int]) -> None:
        for label, count in losses.items():
            reserve.spend({label: min(count, reserve[label])})

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
