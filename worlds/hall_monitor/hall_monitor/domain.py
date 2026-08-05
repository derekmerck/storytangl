from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from tangl.core import Selector
from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import ContentFragment
from tangl.mechanics.credentials import (
    CredentialDefinition,
    CredentialStatus,
    FailureMode,
    Restrictions,
    RestrictionLevel,
)
from tangl.mechanics.presence.look import HasSimpleLook
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
    CredentialCaseResult,
    CredentialDisposition,
    CredentialPresentationProfile,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.mechanics.games.credentials_roster import (
    ScenarioOffer,
    ShiftSpec,
    generate_roster,
)
from tangl.story import Action, Block, on_journal
from tangl.story.presentation import render_text_as
from tangl.vm import on_provision, on_update
from tangl.vm.ctx import VmPhaseCtx


HALL_RULES = {
    "upper": {
        "academic": RestrictionLevel.WITH_PERMIT,
        "activity": RestrictionLevel.WITH_PERMIT,
        "off_campus": RestrictionLevel.WITH_PERMIT,
        "uniform": RestrictionLevel.WITH_ID,
        "medicine": RestrictionLevel.WITH_PERMIT,
        "records": RestrictionLevel.WITH_PERMIT,
    },
    "lower": {
        "academic": RestrictionLevel.WITH_PERMIT,
        "activity": RestrictionLevel.WITH_PERMIT,
        "off_campus": RestrictionLevel.WITH_PERMIT,
        "uniform": RestrictionLevel.WITH_PERMIT,
        "medicine": RestrictionLevel.WITH_PERMIT,
        "records": RestrictionLevel.WITH_PERMIT,
    },
    "exchange": {
        "academic": RestrictionLevel.WITH_PERMIT,
        "activity": RestrictionLevel.WITH_PERMIT,
        "off_campus": RestrictionLevel.WITH_PERMIT,
        "uniform": RestrictionLevel.WITH_PERMIT,
        "medicine": RestrictionLevel.WITH_PERMIT,
        "records": RestrictionLevel.WITH_PERMIT,
    },
}

HALL_PRESENTATION = CredentialPresentationProfile(
    indication_labels={
        "academic": "academic",
        "activity": "activity",
        "off_campus": "off-campus",
        "uniform": "uniform",
        "medicine": "medicine",
        "records": "records",
    },
    document_labels={
        "academic": "hall pass",
        "activity": "activity pass",
        "off_campus": "off-campus pass",
        "uniform": "uniform waiver",
        "medicine": "doctor's note",
        "records": "office pass",
    },
    identity_label="student ID",
    identity_description="A laminated student identification card.",
    document_description="{document}.",
    ordinary_attestation_template=(
        "The {issuer_group} signature appears in blue ink."
    ),
    missing_attestation_template="The {issuer_group} signature line is blank.",
    alternate_attestation_template=(
        "The {issuer_group} signature is written in a heavy, unfamiliar hand."
    ),
    ordinary_validity_template="The pass is marked “Valid for this period.”",
    unusual_date_validity_template="The period box is marked “Period 9.”",
    past_validity_template="The pass is marked “Valid for last period.”",
    possession_description="A student openly declares {indication}.",
    status_text={
        CredentialStatus.MISSING_SEAL: "The required teacher signature is missing.",
        CredentialStatus.BAD_DATE: "The date on the pass is wrong.",
        CredentialStatus.EXPIRED: "The pass has expired.",
        CredentialStatus.FORGED: "The teacher signature is forged.",
        CredentialStatus.WRONG_HOLDER: "The student ID does not match this document.",
    },
    holder_mismatch_text="The student ID does not match this pass.",
    packet_inconsistency_text="The student's papers do not satisfy the hall rules.",
    move_labels={"request_document": "Ask for a corrected {document}"},
    decision_labels={
        "pass": "Allow onward",
        "deny": "Send back to class",
        "arrest": "Send to the office",
    },
    journal_text={
        "request_document": "You ask for a corrected {document}.",
        "request_document_cleared": "A teacher-signed replacement is produced.",
        "request_document_verified": "The student presents the same sound pass.",
        "request_document_confirmed": "No valid school document is forthcoming.",
        "request_document_not_applicable": "There is no school pass to correct.",
    },
)

_HALL_FAILURES = (
    FailureMode.MISSING_PERMIT,
    FailureMode.UNSEALED_PERMIT,
    FailureMode.FORGED_PERMIT,
    FailureMode.WRONG_HOLDER_PERMIT,
    FailureMode.MISSING_ID,
    FailureMode.EXPIRED_ID,
    FailureMode.FAKE_ID,
)


def _special_student() -> ScenarioOffer:
    """Return the recurring lower-school medical-pass case for every shift."""

    return ScenarioOffer(
        target_disposition=CredentialDisposition.DENY,
        candidate_name="Mira Quill",
        region="lower",
        purpose="medicine",
        failure_modes=[FailureMode.UNSEALED_PERMIT],
        presented_documents_override={
            "student ID": "A laminated lower-school student identification card.",
            "doctor's note": "A doctor's note for an inhaler, lacking the nurse's signature.",
        },
        hidden_facts_override={
            "doctor's note": "The required nurse signature is missing.",
        },
        packet_hidden_facts_override={
            "packet consistency": "The student's papers do not satisfy the hall rules.",
        },
    )


def _hall_offers(
    *,
    encounters: int,
    disposition_distribution: dict[CredentialDisposition, float],
    seed: int,
) -> list[ScenarioOffer]:
    """Generate one configured school shift through the shared roster funnel."""

    return generate_roster(
        ShiftSpec(
            rules=Restrictions.from_map(HALL_RULES),
            encounters=encounters,
            origin_distribution={"upper": 0.4, "lower": 0.4, "exchange": 0.2},
            disposition_distribution=disposition_distribution,
            purpose_pool=("academic", "activity", "off_campus"),
            allowed_failure_modes=_HALL_FAILURES,
            pinned=(_special_student(),),
            seed=seed,
        )
    )


class HallMonitorCredentialsGame(CredentialsGame):
    """School-specific credentials shift with the bounded school catalog."""

    restriction_map: Restrictions = Field(
        default_factory=lambda: Restrictions.from_map(HALL_RULES)
    )
    catalog_ref: str = "school"
    presentation: CredentialPresentationProfile = Field(
        default_factory=lambda: HALL_PRESENTATION.model_copy(deep=True)
    )


class HallMonitorConsequence(BaseModelPlus):
    """World-authored later fate for one completed Hall Monitor case.

    Why
    ---
    Credentials records the mechanical receipt. Hall Monitor owns the meaning
    and the later narration of that receipt.
    """

    source_case_index: int
    bearer_id: UUID
    outcome: Literal["inhaler_withheld", "inhaler_allowed"]


class HallMonitorBlock(HasGame, Block):
    """Script-configured Hall Monitor scenario instance."""

    encounters: int = 5
    disposition_distribution: dict[CredentialDisposition, float] = Field(
        default_factory=lambda: {
            CredentialDisposition.PASS: 0.5,
            CredentialDisposition.DENY: 0.3,
            CredentialDisposition.ARREST: 0.2,
        }
    )
    seed: int = 20260719
    inhaler_case_index: int = 0
    consequences: list[HallMonitorConsequence] = Field(
        default_factory=list,
        json_schema_extra={"include": True},
    )

    _game_class = HallMonitorCredentialsGame
    _game_handler_class = CredentialsGameHandler

    @model_validator(mode="after")
    def _configure_game(self) -> HallMonitorBlock:
        if self.game_state is None:
            self.game_state = HallMonitorCredentialsGame(
                roster=[],
                offers=_hall_offers(
                    encounters=self.encounters,
                    disposition_distribution=self.disposition_distribution,
                    seed=self.seed,
                )
            )
        return self


class HallMonitorConsequenceBlock(Block):
    """Later attendance-note beat that reveals a recorded Hall Monitor fate.

    Why
    ---
    A completed credential disposition is a mechanical receipt. This ordinary
    later block makes any Hall Monitor interpretation visible without granting
    it same-turn frontier or namespace visibility.
    """

    source_block_label: str = "morning_shift"
    return_block_label: str = "returning_student"


class HallMonitorReturnBlock(HasGame, Block):
    """One pre-authored return encounter prepared from the attendance note.

    Why
    ---
    The node is ordinary authored topology. Its game is configured only after
    the first case receipt exists, during the predecessor's PLANNING pass.
    """

    _game_class = HallMonitorCredentialsGame
    _game_handler_class = CredentialsGameHandler


@on_update(wants_caller_kind=HallMonitorBlock, wants_exact_kind=False)
def record_hall_monitor_consequence(
    *,
    caller: HallMonitorBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Record Mira's later outcome after the credentials disposition commits."""

    game = caller.game
    if not game.case_results:
        return None
    result = game.case_results[-1]
    if result.case_index != caller.inhaler_case_index:
        return None
    if any(fact.source_case_index == result.case_index for fact in caller.consequences):
        return None

    if result.chosen_disposition is CredentialDisposition.DENY:
        outcome: Literal["inhaler_withheld", "inhaler_allowed"] = "inhaler_withheld"
    elif result.chosen_disposition is CredentialDisposition.PASS:
        outcome = "inhaler_allowed"
    else:
        return None

    caller.consequences.append(
        HallMonitorConsequence(
            source_case_index=result.case_index,
            bearer_id=result.bearer_id,
            outcome=outcome,
        )
    )
    return None


@on_provision(wants_caller_kind=HallMonitorConsequenceBlock, wants_exact_kind=False)
def prepare_hall_monitor_return(
    *,
    caller: HallMonitorConsequenceBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Configure the authored return before its successor is presented."""

    source = caller.graph.find_one(Selector(label=caller.source_block_label))
    return_block = caller.graph.find_one(Selector(label=caller.return_block_label))
    if not isinstance(source, HallMonitorBlock) or not isinstance(
        return_block,
        HallMonitorReturnBlock,
    ):
        raise LookupError("Hall Monitor return topology is incomplete")
    if not source.consequences:
        return None

    consequence = source.consequences[-1]
    if return_block.game_state is None:
        prior_result = source.game.case_results[consequence.source_case_index]
        if prior_result.bearer_id != consequence.bearer_id:
            raise ValueError("Hall Monitor consequence does not match its source receipt")
        return_block.game_state = HallMonitorCredentialsGame(
            roster=[],
            offers=[
                ScenarioOffer(
                    target_disposition=CredentialDisposition.PASS,
                    region="lower",
                    purpose="medicine",
                    candidate_name="Returning student",
                    bearer_id=consequence.bearer_id,
                    prior_case_results=[prior_result],
                    presented_documents_override={
                        "student ID": "A current student identification card.",
                        "doctor's note": "A fresh nurse-signed note for an inhaler.",
                    },
                )
            ]
        )
    if not any(
        caller.edges_out(Selector(has_kind=Action, successor_id=return_block.uid)),
    ):
        Action(
            registry=caller.graph,
            predecessor_id=caller.uid,
            successor_id=return_block.uid,
            text="Meet the returning student",
            tags={"dynamic", "hall_monitor_return"},
        )
    return None


@on_journal(wants_caller_kind=HallMonitorConsequenceBlock, wants_exact_kind=False)
def render_hall_monitor_consequence(
    *,
    caller: HallMonitorConsequenceBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> ContentFragment | None:
    """Reveal recorded Hall Monitor consequences only at the later note beat."""

    source = caller.graph.find_one(Selector(label=caller.source_block_label))
    if not isinstance(source, HallMonitorBlock) or not source.consequences:
        return None
    consequence = source.consequences[-1]
    bearer = caller.graph.get(consequence.bearer_id)
    if not isinstance(bearer, HasSimpleLook):
        raise LookupError(f"Hall Monitor bearer {consequence.bearer_id} is not present")
    name = bearer.get_label()
    presence = render_text_as(bearer, "presence_description", ctx=ctx)
    subject = f"{name}, {presence}," if presence else name
    if consequence.outcome == "inhaler_withheld":
        content = (
            f"{subject} was sent back to class. Their inhaler remained at the "
            "hall desk while the nurse's unsigned note was checked."
        )
    else:
        content = f"{subject} reached the nurse's office with their inhaler."
    return ContentFragment(
        content=content,
        source_id=consequence.bearer_id,
        tags={"hall_monitor_consequence"},
    )


@on_journal(wants_caller_kind=HallMonitorReturnBlock, wants_exact_kind=False)
def render_hall_monitor_return(
    *,
    caller: HallMonitorReturnBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> ContentFragment | None:
    """Recognize the returning bearer through their live presence projection."""

    game = caller.game
    if game.history or not game.active_case.prior_case_results:
        return None
    prior_result = game.active_case.prior_case_results[0]
    bearer = game.active_case.packet_manager.resolve_subject(prior_result.bearer_id)
    name = bearer.get_label()
    presence = render_text_as(bearer, "presence_description", ctx=ctx)
    subject = f"{name}, {presence}," if presence else name
    return ContentFragment(
        content=(
            f"{subject} returns after this morning's decision with a fresh nurse-signed note."
        ),
        source_id=bearer.uid,
        tags={"hall_monitor_return"},
    )


HallMonitorBlock.model_rebuild(_types_namespace={"UUID": UUID})
