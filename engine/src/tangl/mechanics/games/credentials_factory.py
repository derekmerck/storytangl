"""
Procedural candidate factory (Phase A.2).

Builds a fully valid credential packet for an intent against the day's rules,
then degrades it with explicit failure modes. Generation is **start correct,
then degrade**: every candidate begins from a valid packet, and corruptions are
applied only as the chosen failure modes dictate, so the only discrepancies
present are the intended ones (the doctrine from the scratch
``credentialed.py::generate_credentials``).

These functions are pure and on-demand -- they just materialize ``CredentialCase``
data and validate against :func:`~tangl.mechanics.games.credentials_game.derive_disposition`.
The day spec, origin/disposition sampling, and lazy roster of *offers* are Phase
A.3 and live elsewhere; this module is only the case factory the sampler will
call.
"""
from __future__ import annotations

import random
from collections.abc import Iterable, Sequence

from .credentials_enums import (
    ContrabandItem,
    CredentialStatus,
    CredentialToken,
    FailureClass,
    FailureMode,
    Indication,
    Region,
    RestrictionLevel,
    Restrictions,
)
from .credentials_game import CredentialCase

# Contraband used by smuggling / relinquish failures when the intent itself
# carries none. Weapons are permit-gated (not anonymous) in the usual rule sets,
# so a declared one with no permit reads as a mitigatable infraction.
_DEFAULT_CONTRABAND = Indication.WEAPON


def build_valid(
    region: Region,
    purpose: Indication,
    restrictions: Restrictions,
    *,
    candidate_name: str = "Traveler",
    contraband: Sequence[Indication] = (),
) -> CredentialCase:
    """Assemble a fully valid packet for ``purpose`` (+ declared contraband).

    The result derives to PASS under ``restrictions``. Declared contraband must be
    permittable; requesting a FORBIDDEN possession raises, since no valid packet
    can carry it (fail loud rather than return a non-valid case).
    """

    case = CredentialCase(
        candidate_name=candidate_name,
        region=region,
        purpose=purpose,
        presented_documents={},
        hidden_facts={},
        packet_hidden_facts={},
    )
    level = restrictions.level_for(region, purpose, RestrictionLevel.ANONYMOUS)
    if level.requires_id:
        case.id_card = CredentialToken(indication=purpose, status=CredentialStatus.VALID)
    if level.requires_permit:
        case.packet.append(
            CredentialToken(
                indication=purpose,
                status=CredentialStatus.VALID,
                requires_id=True,
                holder_matches=True,
            )
        )

    for c_ind in contraband:
        c_level = restrictions.level_for(region, c_ind, RestrictionLevel.FORBIDDEN)
        if c_level in (RestrictionLevel.CRIMINAL, RestrictionLevel.FORBIDDEN):
            raise ValueError(
                f"Cannot build a valid case with criminal/forbidden contraband: "
                f"{c_ind.value} in {region.value}."
            )
        if c_level.requires_permit:
            case.packet.append(
                CredentialToken(
                    indication=c_ind,
                    status=CredentialStatus.VALID,
                    requires_id=True,
                    holder_matches=True,
                )
            )
        case.possessions.append(ContrabandItem(indication=c_ind, concealed=False))

    return case


def _purpose_permit(case: CredentialCase) -> CredentialToken | None:
    return case.credential_for(case.get_purpose())


def applies_to(mode: FailureMode, case: CredentialCase) -> bool:
    """Whether ``mode`` can be applied to ``case`` (something exists to corrupt)."""

    match mode:
        case (
            FailureMode.MISSING_PERMIT
            | FailureMode.UNSEALED_PERMIT
            | FailureMode.FORGED_PERMIT
            | FailureMode.WRONG_HOLDER_PERMIT
        ):
            return _purpose_permit(case) is not None
        case FailureMode.MISSING_ID | FailureMode.EXPIRED_ID | FailureMode.FAKE_ID:
            return case.id_card is not None
        case FailureMode.UNPERMITTED_CONTRABAND | FailureMode.CONCEALED_CONTRABAND:
            return True
    return False


def apply_failure(mode: FailureMode, case: CredentialCase) -> None:
    """Mutate ``case`` in place to exhibit ``mode``. No-op if not applicable."""

    permit = _purpose_permit(case)
    match mode:
        case FailureMode.MISSING_PERMIT:
            if permit is not None:
                case.packet.remove(permit)
        case FailureMode.UNSEALED_PERMIT:
            if permit is not None:
                permit.status = CredentialStatus.MISSING_SEAL
        case FailureMode.FORGED_PERMIT:
            if permit is not None:
                permit.status = CredentialStatus.FORGED
        case FailureMode.WRONG_HOLDER_PERMIT:
            if permit is not None:
                permit.holder_matches = False
        case FailureMode.MISSING_ID:
            case.id_card = None
        case FailureMode.EXPIRED_ID:
            if case.id_card is not None:
                case.id_card.status = CredentialStatus.EXPIRED
        case FailureMode.FAKE_ID:
            if case.id_card is not None:
                case.id_card.status = CredentialStatus.WRONG_HOLDER
        case FailureMode.UNPERMITTED_CONTRABAND:
            case.possessions.append(
                ContrabandItem(indication=_DEFAULT_CONTRABAND, concealed=False)
            )
        case FailureMode.CONCEALED_CONTRABAND:
            case.possessions.append(
                ContrabandItem(indication=_DEFAULT_CONTRABAND, concealed=True)
            )


def degrade(case: CredentialCase, modes: Iterable[FailureMode]) -> CredentialCase:
    """Apply each failure mode to ``case`` in place and return it."""

    for mode in modes:
        apply_failure(mode, case)
    return case


_STATUS_FINDINGS = {
    CredentialStatus.MISSING_SEAL: "The issuing seal is missing.",
    CredentialStatus.BAD_DATE: "The issue date is wrong.",
    CredentialStatus.EXPIRED: "The credential has expired.",
    CredentialStatus.FORGED: "The seal is a forgery.",
    CredentialStatus.WRONG_HOLDER: "The holder does not match this document.",
}


def render_narrative(case: CredentialCase) -> CredentialCase:
    """Populate the inspect-loop strings from the structured truth, in place.

    Gives a generated case the ``presented_documents`` / ``hidden_facts`` /
    ``packet_hidden_facts`` the v1 inspect loop needs. Document-level infractions
    (bad/forged seal, holder mismatch) surface here; missing documents and
    concealed contraband are detected by Phase B follow-up moves, not by plain
    inspection, so they are not rendered as findings.
    """

    documents: dict[str, str] = {}
    findings: dict[str, str] = {}

    if case.id_card is not None:
        documents["passport"] = "An identity document."
        if not case.id_card.status.is_valid:
            findings["passport"] = _STATUS_FINDINGS[case.id_card.status]

    for token in case.packet:
        label = f"{token.indication.value} permit"
        documents[label] = f"A {token.indication.value} permit."
        if not token.status.is_valid:
            findings[label] = _STATUS_FINDINGS[token.status]
        elif not token.holder_matches:
            findings[label] = "The permit's holder does not match the bearer id."

    for item in case.possessions:
        if not item.concealed:
            documents[f"declared {item.indication.value}"] = f"Openly declared {item.indication.value}."

    case.presented_documents = documents
    case.hidden_facts = findings
    case.packet_hidden_facts = (
        {"packet consistency": "The packet does not satisfy the checkpoint rules as presented."}
        if findings
        else {}
    )
    return case


def make_case(
    region: Region,
    purpose: Indication,
    restrictions: Restrictions,
    *,
    failure_modes: Sequence[FailureMode] = (),
    candidate_name: str = "Traveler",
    contraband: Sequence[Indication] = (),
) -> CredentialCase:
    """Tier 2 entry: build a valid packet, degrade it, and render its narrative."""

    case = build_valid(
        region, purpose, restrictions, candidate_name=candidate_name, contraband=contraband
    )
    degrade(case, failure_modes)
    return render_narrative(case)


def applicable_modes(
    case: CredentialCase,
    failure_class: FailureClass | None = None,
) -> list[FailureMode]:
    """Failure modes that can be applied to ``case``, optionally filtered by class."""

    modes = [mode for mode in FailureMode if applies_to(mode, case)]
    if failure_class is not None:
        modes = [mode for mode in modes if mode.failure_class is failure_class]
    return modes


def sample_failure_mode(
    case: CredentialCase,
    failure_class: FailureClass,
    rng: random.Random | None = None,
) -> FailureMode | None:
    """Pick an applicable failure mode of ``failure_class`` for ``case``, if any."""

    choices = applicable_modes(case, failure_class)
    if not choices:
        return None
    return (rng or random.Random()).choice(choices)
