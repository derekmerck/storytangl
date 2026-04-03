"""
Kim's Game style memory-and-picking contest.

The player spends a limited number of inspections on memory cues, then commits
to which item went missing from the tray.
"""
from __future__ import annotations

import random
from typing import ClassVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment

from .enums import RoundResult
from .game import Game
from .picking_game import PickingGame, PickingGameHandler, PickingMove


KimMove = PickingMove


class KimGame(PickingGame):
    """State for a light memory-and-guess picking contest."""

    visible_items: list[str] = Field(
        default_factory=lambda: [
            "ivory die",
            "silver thimble",
            "glass marble",
            "wax seal",
        ]
    )
    hidden_facts: dict[str, str] = Field(
        default_factory=lambda: {
            "material": "The missing piece felt cool and metallic against the palm.",
            "size": "It was the smallest thing on the tray.",
            "letter": "Its name began with the same hiss as silk.",
            "misdirect": "You keep remembering the wax seal because it was the boldest color there.",
        }
    )
    inspectable_targets: list[str] = Field(
        default_factory=lambda: ["material", "size", "letter", "misdirect"]
    )
    missing_item: str | None = None
    cue_budget: int = 2
    selection_seed: int | None = None

    remaining_cues: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )

    @property
    def tray_items(self) -> list[str]:
        return self.visible_items

    @property
    def cue_text_by_label(self) -> dict[str, str]:
        return self.hidden_facts

    @property
    def inspected_cues(self) -> list[str]:
        return self.inspected_targets

    @property
    def revealed_cues(self) -> list[str]:
        return list(self.revealed_findings.values())

    def get_visible_items(self) -> list[str]:
        return list(self.tray_items)

    def get_inspect_targets(self) -> list[str]:
        return list(self.cue_text_by_label)

    def get_hidden_facts(self) -> dict[str, str]:
        return dict(self.cue_text_by_label)

    def get_decision_targets(self) -> list[str]:
        return list(self.tray_items)

    def describe_inspect_target(self, target: str) -> str:
        return f"the {target} cue"

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "kim_tray_items": list(self.tray_items),
                "kim_remaining_cues": self.remaining_cues,
                "kim_inspected_cues": list(self.inspected_cues),
                "kim_revealed_cues": list(self.revealed_cues),
            }
        )
        if self.result.is_terminal:
            namespace["kim_missing_item"] = self.missing_item
        return namespace


class KimGameHandler(PickingGameHandler[KimGame]):
    """Handler for a small cue-driven Kim's Game loop."""

    game_cls: ClassVar[type[Game]] = KimGame

    def on_setup(self, game: KimGame) -> None:
        if game.missing_item is None:
            chooser = random.Random(game.selection_seed)
            game.missing_item = chooser.choice(game.tray_items)
        game.remaining_cues = game.cue_budget
        game.decision_options = list(game.tray_items)
        game.round_detail = {
            "outcome": "opening",
            "tray_items": list(game.tray_items),
        }

    def get_available_inspect_targets(self, game: KimGame) -> list[str]:
        if game.remaining_cues <= 0:
            return []
        return super().get_available_inspect_targets(game)

    def get_available_decision_targets(self, game: KimGame) -> list[str]:
        return [item for item in game.tray_items]

    def get_move_label(self, game: KimGame, move: KimMove) -> str:
        if move.kind == "inspect":
            return f"Inspect the {move.target} cue"
        return f"Guess {move.target}"

    def resolve_inspection(
        self,
        game: KimGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        game.remaining_cues -= 1
        clue = game.cue_text_by_label[target]
        game.revealed_findings[target] = clue
        detail["clue"] = clue
        detail["finding"] = clue
        detail["remaining_cues"] = game.remaining_cues
        detail["outcome"] = "continue"
        return RoundResult.CONTINUE

    def resolve_decision(
        self,
        game: KimGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        if target == game.missing_item:
            game.score["player"] = 1
            detail["outcome"] = "correct_guess"
            return RoundResult.WIN

        game.score["opponent"] = 1
        detail["outcome"] = "wrong_guess"
        detail["missing_item"] = game.missing_item
        return RoundResult.LOSE

    def build_round_notes(
        self,
        game: KimGame,
        player_move: KimMove,
        opponent_move: KimMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(super().build_round_notes(game, player_move, opponent_move, round_result) or {})
        detail["revealed_cues"] = list(game.revealed_cues)
        if round_result != RoundResult.CONTINUE:
            detail["missing_item"] = game.missing_item
        return detail

    def get_journal_fragments(self, game: KimGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        action = last_round.player_move.kind
        target = last_round.player_move.target
        notes = last_round.notes or {}

        if action == "inspect":
            return [
                ContentFragment(content=f"You press on the {target} cue."),
                ContentFragment(content=str(notes.get("clue", ""))),
                ContentFragment(
                    content=f"{notes.get('remaining_cues', game.remaining_cues)} cues remain."
                ),
            ]

        outcome_line = (
            "The tray clicks into focus. You name the missing object correctly."
            if last_round.result == RoundResult.WIN
            else f"The answer slips away. The missing item was {notes.get('missing_item', game.missing_item)}."
        )
        return [
            ContentFragment(content=f"You name {target}."),
            ContentFragment(content=outcome_line),
        ]
