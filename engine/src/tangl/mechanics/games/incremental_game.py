"""
Incremental shell kernel.

This family models a single-player planning loop with persistent assignments,
explicit upkeep, optional builds and promotions, and cycle-based production.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pydantic import Field

from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import ContentFragment

from .enums import GameResult, RoundResult
from .game import Game
from .handler import GameHandler


@dataclass(frozen=True)
class IncrementalMove:
    """Structured move for the incremental shell."""

    kind: str
    target: str | None = None


class TaskSpec(BaseModelPlus):
    """Per-worker production rule for an unlocked task."""

    produces: dict[str, int] = Field(default_factory=dict)
    consumes: dict[str, int] = Field(default_factory=dict)


class BuildSpec(BaseModelPlus):
    """Immediate build option for the incremental shell."""

    cost: dict[str, int] = Field(default_factory=dict)
    infrastructure_gain: dict[str, int] = Field(default_factory=dict)
    resource_gain: dict[str, int] = Field(default_factory=dict)
    worker_gain: int = 0
    unlock_tasks: list[str] = Field(default_factory=list)
    unlock_builds: list[str] = Field(default_factory=list)
    unlock_promotions: list[str] = Field(default_factory=list)


class PromotionSpec(BaseModelPlus):
    """Resource-to-specialist conversion option."""

    cost: dict[str, int] = Field(default_factory=dict)
    output: dict[str, int] = Field(default_factory=dict)
    requires_infrastructure: dict[str, int] = Field(default_factory=dict)
    worker_cost: int = 1


class IncrementalGame(Game[IncrementalMove]):
    """Single-player planning shell for incremental loops."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = None

    starting_resources: dict[str, int] = Field(default_factory=dict)
    starting_workers: int = 0
    task_specs: dict[str, TaskSpec] = Field(default_factory=dict)
    build_specs: dict[str, BuildSpec] = Field(default_factory=dict)
    promotion_specs: dict[str, PromotionSpec] = Field(default_factory=dict)
    upkeep: dict[str, int] = Field(default_factory=dict)
    victory_resources: dict[str, int] = Field(default_factory=dict)
    loss_if_upkeep_unpaid: bool = True

    unlocked_tasks: list[str] = Field(default_factory=list)
    unlocked_builds: list[str] = Field(default_factory=list)
    unlocked_promotions: list[str] = Field(default_factory=list)

    resources: dict[str, int] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    worker_pool: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    task_assignments: dict[str, int] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    infrastructure: dict[str, int] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    pending_rewards: dict[str, int] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    cycle: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "incremental_cycle": self.cycle,
                "incremental_resources": dict(self.resources),
                "incremental_worker_pool": self.worker_pool,
                "incremental_task_assignments": dict(self.task_assignments),
                "incremental_infrastructure": dict(self.infrastructure),
                "incremental_unlocked_tasks": list(self.unlocked_tasks),
                "incremental_unlocked_builds": list(self.unlocked_builds),
                "incremental_unlocked_promotions": list(self.unlocked_promotions),
                "incremental_pending_rewards": dict(self.pending_rewards),
            }
        )
        return namespace


class IncrementalGameHandler(GameHandler[IncrementalGame]):
    """Handler for the incremental shell kernel."""

    game_cls: ClassVar[type[Game]] = IncrementalGame

    def on_setup(self, game: IncrementalGame) -> None:
        game.resources = dict(game.starting_resources)
        game.worker_pool = game.starting_workers
        game.task_assignments = {name: 0 for name in game.task_specs}
        game.infrastructure = {}
        game.pending_rewards = {}
        game.cycle = 0
        game.round_detail = {
            "outcome": "opening",
            "resources": dict(game.resources),
            "worker_pool": game.worker_pool,
        }

    def get_available_moves(self, game: IncrementalGame) -> list[IncrementalMove]:
        moves: list[IncrementalMove] = []
        if game.worker_pool > 0:
            for task_name in game.unlocked_tasks:
                moves.append(IncrementalMove(kind="assign", target=task_name))

        for task_name, count in game.task_assignments.items():
            if count > 0:
                moves.append(IncrementalMove(kind="unassign", target=task_name))

        for build_name in game.unlocked_builds:
            build = game.build_specs.get(build_name)
            if build is not None and self._can_afford(game.resources, build.cost):
                moves.append(IncrementalMove(kind="build", target=build_name))

        for promotion_name in game.unlocked_promotions:
            promotion = game.promotion_specs.get(promotion_name)
            if (
                promotion is not None
                and game.worker_pool >= promotion.worker_cost
                and self._can_afford(game.resources, promotion.cost)
                and self._meets_requirements(game.infrastructure, promotion.requires_infrastructure)
            ):
                moves.append(IncrementalMove(kind="promote", target=promotion_name))

        moves.append(IncrementalMove(kind="end_cycle"))
        return moves

    def get_move_label(self, game: IncrementalGame, move: IncrementalMove) -> str:
        if move.kind == "assign":
            return f"Assign 1 worker to {move.target}"
        if move.kind == "unassign":
            return f"Unassign 1 worker from {move.target}"
        if move.kind == "build":
            return f"Build {move.target}"
        if move.kind == "promote":
            return f"Promote 1 worker into {move.target}"
        return "End cycle"

    def resolve_round(
        self,
        game: IncrementalGame,
        player_move: IncrementalMove,
        opponent_move: IncrementalMove | None,
    ) -> RoundResult:
        detail: dict[str, object] = {
            "action": player_move.kind,
            "target": player_move.target,
        }

        if player_move.kind == "assign":
            self._assign_worker(game, player_move.target or "")
            detail["outcome"] = "assigned"
            detail["worker_pool"] = game.worker_pool
            detail["task_assignments"] = dict(game.task_assignments)
            game.round_detail = detail
            return RoundResult.CONTINUE

        if player_move.kind == "unassign":
            self._unassign_worker(game, player_move.target or "")
            detail["outcome"] = "unassigned"
            detail["worker_pool"] = game.worker_pool
            detail["task_assignments"] = dict(game.task_assignments)
            game.round_detail = detail
            return RoundResult.CONTINUE

        if player_move.kind == "build":
            self._apply_build(game, player_move.target or "", detail)
            detail["outcome"] = "built"
            game.round_detail = detail
            return RoundResult.CONTINUE

        if player_move.kind == "promote":
            self._apply_promotion(game, player_move.target or "", detail)
            detail["outcome"] = "promoted"
            game.round_detail = detail
            return RoundResult.CONTINUE

        result = self._resolve_cycle(game, detail)
        game.round_detail = detail
        return result

    def evaluate(self, game: IncrementalGame) -> GameResult:
        if game.victory_resources and self._meets_requirements(game.resources, game.victory_resources):
            return GameResult.WIN
        if game.score["player"] > 0:
            return GameResult.WIN
        if game.score["opponent"] > 0:
            return GameResult.LOSE
        return GameResult.IN_PROCESS

    def build_round_notes(
        self,
        game: IncrementalGame,
        player_move: IncrementalMove,
        opponent_move: IncrementalMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["resources"] = dict(game.resources)
        detail["worker_pool"] = game.worker_pool
        detail["task_assignments"] = dict(game.task_assignments)
        detail["cycle"] = game.cycle
        return detail

    def get_journal_fragments(self, game: IncrementalGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        action = notes.get("action")
        target = notes.get("target")

        if action == "assign":
            return [
                ContentFragment(content=f"You assign a worker to {target}."),
                ContentFragment(
                    content=f"{notes.get('worker_pool', game.worker_pool)} workers remain unassigned."
                ),
            ]

        if action == "unassign":
            return [
                ContentFragment(content=f"You pull a worker off {target}."),
                ContentFragment(
                    content=f"{notes.get('worker_pool', game.worker_pool)} workers now stand free."
                ),
            ]

        if action == "build":
            return [
                ContentFragment(content=f"You build {target}."),
                ContentFragment(content=self._resource_line(notes.get("resources", game.resources))),
            ]

        if action == "promote":
            return [
                ContentFragment(content=f"You promote a worker into {target}."),
                ContentFragment(content=self._resource_line(notes.get("resources", game.resources))),
            ]

        fragments = [
            ContentFragment(content=f"Cycle {notes.get('cycle', game.cycle)} resolves."),
            ContentFragment(content=self._resource_line(notes.get("resources", game.resources))),
        ]
        if last_round.result == RoundResult.WIN:
            fragments.append(ContentFragment(content="The shell finally tips into a winning surplus."))
        elif last_round.result == RoundResult.LOSE:
            fragments.append(ContentFragment(content="Upkeep overwhelms the shell and the loop collapses."))
        return fragments

    def _assign_worker(self, game: IncrementalGame, task_name: str) -> None:
        game.worker_pool -= 1
        game.task_assignments[task_name] = game.task_assignments.get(task_name, 0) + 1

    def _unassign_worker(self, game: IncrementalGame, task_name: str) -> None:
        game.worker_pool += 1
        game.task_assignments[task_name] = max(game.task_assignments.get(task_name, 0) - 1, 0)

    def _apply_build(self, game: IncrementalGame, build_name: str, detail: dict[str, object]) -> None:
        build = game.build_specs[build_name]
        self._spend(game.resources, build.cost)
        self._earn(game.resources, build.resource_gain)
        self._earn(game.infrastructure, build.infrastructure_gain)
        game.worker_pool += build.worker_gain
        self._unlock(game.unlocked_tasks, build.unlock_tasks)
        self._unlock(game.unlocked_builds, build.unlock_builds)
        self._unlock(game.unlocked_promotions, build.unlock_promotions)
        detail["resources"] = dict(game.resources)
        detail["infrastructure"] = dict(game.infrastructure)

    def _apply_promotion(
        self,
        game: IncrementalGame,
        promotion_name: str,
        detail: dict[str, object],
    ) -> None:
        promotion = game.promotion_specs[promotion_name]
        self._spend(game.resources, promotion.cost)
        self._earn(game.resources, promotion.output)
        game.worker_pool -= promotion.worker_cost
        detail["resources"] = dict(game.resources)
        detail["worker_pool"] = game.worker_pool

    def _resolve_cycle(self, game: IncrementalGame, detail: dict[str, object]) -> RoundResult:
        self._earn(game.resources, game.pending_rewards)
        game.pending_rewards = {}

        if not self._can_afford(game.resources, game.upkeep):
            detail["resources_before_failure"] = dict(game.resources)
            detail["outcome"] = "upkeep_failure"
            if game.loss_if_upkeep_unpaid:
                game.score["opponent"] = 1
                return RoundResult.LOSE
        else:
            self._spend(game.resources, game.upkeep)

        cycle_events: list[str] = []
        for task_name, workers in game.task_assignments.items():
            spec = game.task_specs.get(task_name)
            if spec is None or workers <= 0:
                continue
            for _ in range(workers):
                if not self._can_afford(game.resources, spec.consumes):
                    continue
                self._spend(game.resources, spec.consumes)
                self._earn(game.resources, spec.produces)
                cycle_events.append(task_name)

        game.cycle += 1
        detail["cycle"] = game.cycle
        detail["cycle_events"] = cycle_events
        detail["resources"] = dict(game.resources)
        detail["task_assignments"] = dict(game.task_assignments)
        detail["worker_pool"] = game.worker_pool

        if game.victory_resources and self._meets_requirements(game.resources, game.victory_resources):
            detail["outcome"] = "victory"
            game.score["player"] = 1
            return RoundResult.WIN

        detail["outcome"] = "continue"
        return RoundResult.CONTINUE

    def _can_afford(self, wallet: dict[str, int], cost: dict[str, int]) -> bool:
        return all(wallet.get(label, 0) >= amount for label, amount in cost.items())

    def _meets_requirements(self, wallet: dict[str, int], requirement: dict[str, int]) -> bool:
        return all(wallet.get(label, 0) >= amount for label, amount in requirement.items())

    def _spend(self, wallet: dict[str, int], cost: dict[str, int]) -> None:
        for label, amount in cost.items():
            wallet[label] = wallet.get(label, 0) - amount

    def _earn(self, wallet: dict[str, int], reward: dict[str, int]) -> None:
        for label, amount in reward.items():
            wallet[label] = wallet.get(label, 0) + amount

    def _unlock(self, current: list[str], new_labels: list[str]) -> None:
        for label in new_labels:
            if label not in current:
                current.append(label)

    def _resource_line(self, resources: dict[str, int]) -> str:
        if not resources:
            return "Resources: none."
        parts = [f"{label}={amount}" for label, amount in sorted(resources.items())]
        return "Resources: " + ", ".join(parts) + "."
