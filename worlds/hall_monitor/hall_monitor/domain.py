from __future__ import annotations

from uuid import UUID

from pydantic import Field, model_validator

from tangl.mechanics.credentials import (
    CredentialDefinition,
    CredentialStatus,
    FailureMode,
    Restrictions,
    RestrictionLevel,
)
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
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
from tangl.story import Block


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
    document_description="{document}. Signed for this period.",
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
    """Return the recurring lower-school activity-pass case for every shift."""

    return ScenarioOffer(
        target_disposition=CredentialDisposition.DENY,
        candidate_name="Mira Quill",
        region="lower",
        purpose="activity",
        failure_modes=[FailureMode.UNSEALED_PERMIT],
        presented_documents_override={
            "student ID": "A laminated lower-school student identification card.",
            "activity pass": "An activity pass lacking the teacher's signature.",
        },
        hidden_facts_override={
            "activity pass": "The required teacher signature is missing.",
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

    _game_class = HallMonitorCredentialsGame
    _game_handler_class = CredentialsGameHandler

    @model_validator(mode="after")
    def _configure_game(self) -> HallMonitorBlock:
        if self.game_state is None:
            self.game_state = HallMonitorCredentialsGame(
                offers=_hall_offers(
                    encounters=self.encounters,
                    disposition_distribution=self.disposition_distribution,
                    seed=self.seed,
                )
            )
        return self


HallMonitorBlock.model_rebuild(_types_namespace={"UUID": UUID})
