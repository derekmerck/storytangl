"""
Credential check contest built on the same inspect-and-commit loop.

This is intentionally the small outer game block only: inspect evidence, reveal
findings, then choose a disposition.
"""
from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment

from .enums import RoundResult
from .game import Game
from .picking_game import PickingGame, PickingGameHandler, PickingMove


class CredentialDisposition(Enum):
    """Terminal credential dispositions."""

    PASS = "pass"
    DENY = "deny"
    ARREST = "arrest"


CredentialsMove = PickingMove


class CredentialsGame(PickingGame):
    """State for a compact credential inspection loop."""

    candidate_name: str = "Traveler"
    current_stage: str = Field(
        default="documents",
        json_schema_extra={"reset_field": True},
    )
    required_documents: list[str] = Field(
        default_factory=lambda: ["passport", "travel permit"]
    )
    presented_documents: dict[str, str] = Field(
        default_factory=lambda: {
            "passport": "A worn passport with a blurred seal.",
            "travel permit": "A permit stamped for this week.",
            "baggage": "A lacquered case with a stubborn clasp.",
        }
    )
    hidden_facts: dict[str, str] = Field(
        default_factory=lambda: {
            "passport": "The seal impression is wrong for this border.",
        }
    )
    packet_hidden_facts: dict[str, str] = Field(
        default_factory=lambda: {
            "packet consistency": "The packet does not satisfy the checkpoint rules as presented.",
        }
    )
    checkpoint_rules: list[str] = Field(
        default_factory=lambda: [
            "Travelers need a valid passport.",
            "This route also requires a travel permit.",
        ]
    )
    whitelist_status: bool = False
    blacklist_status: bool = False
    bribe_offer: int = 0
    prior_encounters: list[str] = Field(default_factory=list)
    correct_disposition: CredentialDisposition = CredentialDisposition.DENY
    allow_arrest: bool = True
    inspected_packet_targets: list[str] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    packet_findings: dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )

    @property
    def inspected_documents(self) -> list[str]:
        return [target for target in self.inspected_targets if target in self.presented_documents]

    @property
    def discovered_findings(self) -> dict[str, str]:
        return self.revealed_findings

    @property
    def hidden_findings(self) -> dict[str, str]:
        return self.hidden_facts

    @property
    def disposition(self) -> CredentialDisposition | None:
        if self.terminal_decision is None:
            return None
        return CredentialDisposition(self.terminal_decision)

    def get_visible_items(self) -> list[str]:
        return list(self.presented_documents)

    def get_inspect_targets(self) -> list[str]:
        return list(self.presented_documents)

    def get_hidden_facts(self) -> dict[str, str]:
        return dict(self.hidden_findings)

    def get_decision_targets(self) -> list[str]:
        if self.current_stage == "documents":
            return []
        options = [
            CredentialDisposition.PASS.value,
            CredentialDisposition.DENY.value,
        ]
        if self.allow_arrest:
            options.append(CredentialDisposition.ARREST.value)
        return options

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                "credential_candidate_name": self.candidate_name,
                "credential_required_documents": list(self.required_documents),
                "credential_inspected_documents": list(self.inspected_documents),
                "credential_discovered_findings": dict(self.discovered_findings),
                "credential_num_findings": len(self.discovered_findings),
                "credential_stage": self.current_stage,
                "credential_packet_findings": dict(self.packet_findings),
                "credential_num_packet_findings": len(self.packet_findings),
                "credential_checkpoint_rules": list(self.checkpoint_rules),
                "credential_whitelist_status": self.whitelist_status,
                "credential_blacklist_status": self.blacklist_status,
                "credential_bribe_offer": self.bribe_offer,
                "credential_prior_encounters": list(self.prior_encounters),
                "credential_allow_arrest": self.allow_arrest,
                "credential_disposition": (
                    self.disposition.value if self.disposition is not None else None
                ),
            }
        )
        return namespace


class CredentialsGameHandler(PickingGameHandler[CredentialsGame]):
    """Handler for inspect-and-dispose credential checks."""

    game_cls: ClassVar[type[Game]] = CredentialsGame

    def get_available_inspect_targets(self, game: CredentialsGame) -> list[str]:
        targets = [
            name for name in game.presented_documents if name not in game.inspected_documents
        ]
        if game.current_stage != "documents":
            targets.extend(
                target
                for target in game.packet_hidden_facts
                if target not in game.inspected_packet_targets
            )
        return targets

    def get_move_label(self, game: CredentialsGame, move: CredentialsMove) -> str:
        if move.kind == "inspect":
            if move.target in game.packet_hidden_facts:
                return f"Review {move.target}"
            return f"Inspect {move.target}"
        return f"Choose {move.target}"

    def resolve_inspection(
        self,
        game: CredentialsGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        if target in game.packet_hidden_facts:
            game.inspected_packet_targets.append(target)
            finding = self._packet_finding(game, target)
            if finding is not None:
                game.packet_findings[target] = finding
                detail["finding"] = finding
                detail["outcome"] = "packet_finding"
            else:
                detail["finding"] = "The packet still hangs together under current scrutiny."
                detail["outcome"] = "packet_clear"
            game.current_stage = "packet"
            return RoundResult.CONTINUE

        finding = game.hidden_findings.get(target)
        if finding is not None:
            game.revealed_findings[target] = finding
            detail["finding"] = finding
            detail["outcome"] = "finding"
        else:
            detail["finding"] = "It looks in order."
            detail["outcome"] = "clear"
        game.current_stage = "packet"
        return RoundResult.CONTINUE

    def resolve_decision(
        self,
        game: CredentialsGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        expected = self._expected_disposition(game)
        if game.disposition == expected:
            game.score["player"] = 1
            detail["outcome"] = "correct_disposition"
            return RoundResult.WIN

        game.score["opponent"] = 1
        detail["outcome"] = "wrong_disposition"
        detail["correct_disposition"] = expected.value
        return RoundResult.LOSE

    def build_round_notes(
        self,
        game: CredentialsGame,
        player_move: CredentialsMove,
        opponent_move: CredentialsMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(super().build_round_notes(game, player_move, opponent_move, round_result) or {})
        detail["discovered_findings"] = dict(game.discovered_findings)
        detail["packet_findings"] = dict(game.packet_findings)
        detail["credential_stage"] = game.current_stage
        return detail

    def get_journal_fragments(self, game: CredentialsGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        action = last_round.player_move.kind
        target = last_round.player_move.target
        notes = last_round.notes or {}

        if action == "inspect":
            if target in game.packet_hidden_facts:
                return [
                    ContentFragment(content=f"You review {target}."),
                    ContentFragment(content=str(notes.get("finding", "No new contradiction appears."))),
                ]
            return [
                ContentFragment(content=f"You inspect the {target}."),
                ContentFragment(content=str(notes.get("finding", "Nothing new emerges."))),
            ]

        outcome_line = (
            f"{game.candidate_name} absorbs the ruling without protest."
            if last_round.result == RoundResult.WIN
            else (
                f"The room turns uneasy. The right call was "
                f"{notes.get('correct_disposition', game.correct_disposition.value)}."
            )
        )
        return [
            ContentFragment(content=f"You choose to {target}."),
            ContentFragment(content=outcome_line),
        ]

    def _expected_disposition(self, game: CredentialsGame) -> CredentialDisposition:
        if game.whitelist_status:
            return CredentialDisposition.PASS
        if game.blacklist_status:
            return CredentialDisposition.ARREST if game.allow_arrest else CredentialDisposition.DENY
        return game.correct_disposition

    def _packet_finding(self, game: CredentialsGame, target: str) -> str | None:
        if target not in game.packet_hidden_facts:
            return None
        if game.whitelist_status:
            return "The whitelist seal overrides the usual packet mismatch."
        if game.blacklist_status:
            return "The packet matches a standing blacklist notice at this checkpoint."
        if game.bribe_offer > 0:
            return (
                f"The packet comes with a quiet offer of {game.bribe_offer} in side payment. "
                f"{game.packet_hidden_facts[target]}"
            )
        return game.packet_hidden_facts[target]
