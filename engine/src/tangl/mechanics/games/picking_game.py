"""
Shared inspect-and-reveal picking kernel.

This kernel captures the common shape behind light memory tests, mismatch
inspection, and small validation loops: inspect visible targets, reveal hidden
facts, then commit to a terminal decision.
"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, TypeVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment

from .enums import RoundResult
from .game import Game
from .handler import GameHandler


@dataclass(frozen=True)
class PickingMove:
    """Structured move for inspect-and-commit style picking games."""

    kind: str
    target: str


class PickingGame(Game[PickingMove]):
    """Common state for inspect/reveal/decide loops."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = None

    visible_items: list[str] = Field(default_factory=list)
    inspectable_targets: list[str] = Field(default_factory=list)
    hidden_facts: dict[str, str] = Field(default_factory=dict)
    decision_options: list[str] = Field(default_factory=list)

    inspected_targets: list[str] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    revealed_findings: dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    terminal_decision: str | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    def get_visible_items(self) -> list[str]:
        """Return the visible items currently framing the puzzle."""

        return list(self.visible_items)

    def get_inspect_targets(self) -> list[str]:
        """Return the targets that may be inspected."""

        return list(self.inspectable_targets)

    def get_hidden_facts(self) -> dict[str, str]:
        """Return hidden facts keyed by inspect target."""

        return dict(self.hidden_facts)

    def get_decision_targets(self) -> list[str]:
        """Return the terminal decision options currently available."""

        return list(self.decision_options)

    def describe_inspect_target(self, target: str) -> str:
        """Return a human-readable label for an inspect target."""

        return target

    def describe_decision_target(self, target: str) -> str:
        """Return a human-readable label for a decision target."""

        return target

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "picking_visible_items": self.get_visible_items(),
                "picking_inspectable_targets": self.get_inspect_targets(),
                "picking_hidden_fact_targets": sorted(self.get_hidden_facts()),
                "picking_inspected_targets": list(self.inspected_targets),
                "picking_revealed_findings": dict(self.revealed_findings),
                "picking_num_findings": len(self.revealed_findings),
                "picking_terminal_decision": self.terminal_decision,
                "picking_decision_options": self.get_decision_targets(),
            }
        )
        return namespace


PickingGameT = TypeVar("PickingGameT", bound=PickingGame)


class PickingGameHandler(GameHandler[PickingGameT]):
    """Shared handler for inspect/reveal/decide loops."""

    game_cls: ClassVar[type[Game]] = PickingGame

    def _normalize_move(self, move: Any) -> PickingMove:
        """Coerce legacy tuple moves into the structured move shape."""

        if isinstance(move, PickingMove):
            return move

        if (
            isinstance(move, tuple)
            and len(move) == 2
            and isinstance(move[0], str)
            and isinstance(move[1], str)
        ):
            kind, target = move
            normalized_kind = {
                "guess": "decide",
            }.get(kind, kind)
            return PickingMove(kind=normalized_kind, target=target)

        raise TypeError(f"Unsupported picking move type: {move!r}")

    def get_available_moves(self, game: PickingGameT) -> list[PickingMove]:
        moves: list[PickingMove] = []
        for target in self.get_available_inspect_targets(game):
            moves.append(PickingMove(kind="inspect", target=target))
        for target in self.get_available_decision_targets(game):
            moves.append(PickingMove(kind="decide", target=target))
        return moves

    def get_available_inspect_targets(self, game: PickingGameT) -> list[str]:
        """Return currently available inspect targets."""

        return [
            target
            for target in game.get_inspect_targets()
            if target not in game.inspected_targets
        ]

    def get_available_decision_targets(self, game: PickingGameT) -> list[str]:
        """Return currently available decision options."""

        return list(game.get_decision_targets())

    def get_move_label(self, game: PickingGameT, move: PickingMove) -> str:
        if move.kind == "inspect":
            return f"Inspect {game.describe_inspect_target(move.target)}"
        return f"Choose {game.describe_decision_target(move.target)}"

    def resolve_round(
        self,
        game: PickingGameT,
        player_move: PickingMove,
        opponent_move: PickingMove | None,
    ) -> RoundResult:
        player_move = self._normalize_move(player_move)
        detail: dict[str, object] = {
            "action": player_move.kind,
            "target": player_move.target,
        }

        if player_move.kind == "inspect":
            game.inspected_targets.append(player_move.target)
            result = self.resolve_inspection(game, player_move.target, detail)
        elif player_move.kind == "decide":
            game.terminal_decision = player_move.target
            result = self.resolve_decision(game, player_move.target, detail)
        else:
            raise ValueError(f"Unknown picking move kind: {player_move.kind}")

        game.round_detail = detail
        return result

    @abstractmethod
    def resolve_inspection(
        self,
        game: PickingGameT,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        """Resolve an inspection move and update ``detail`` in-place."""

        raise NotImplementedError

    @abstractmethod
    def resolve_decision(
        self,
        game: PickingGameT,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        """Resolve a terminal decision move and update ``detail`` in-place."""

        raise NotImplementedError

    def build_round_notes(
        self,
        game: PickingGameT,
        player_move: PickingMove,
        opponent_move: PickingMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["inspected_targets"] = list(game.inspected_targets)
        detail["revealed_findings"] = dict(game.revealed_findings)
        detail["terminal_decision"] = game.terminal_decision
        return detail

    def get_journal_fragments(self, game: PickingGameT) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        target = last_round.player_move.target
        if last_round.player_move.kind == "inspect":
            finding = notes.get("finding")
            fragments = [ContentFragment(content=f"You inspect {target}.")]
            if isinstance(finding, str) and finding:
                fragments.append(ContentFragment(content=finding))
            return fragments

        outcome = notes.get("outcome")
        fragments = [ContentFragment(content=f"You choose {target}.")]
        if isinstance(outcome, str) and outcome:
            fragments.append(ContentFragment(content=outcome))
        return fragments
