"""
Procedural candidate factory (Phase A.2).

Builds a fully valid credential packet for an intent against the day's rules,
then degrades it with explicit failure modes. Generation is **start correct,
then degrade**: every candidate begins from a valid packet, and corruptions are
applied only as the chosen failure modes dictate, so the only discrepancies
present are the intended ones (the doctrine from the scratch
``credentialed.py::generate_credentials``).

These functions materialize a ``CredentialCase`` around one owner-bound
``CredentialPacketManager``. The day spec, origin/disposition sampling, and lazy
roster of *offers* are Phase A.3 and live elsewhere; this module is only the
arrival-time factory the sampler calls.
"""
from __future__ import annotations

import random
from collections.abc import Iterable, Sequence

from tangl.core import TokenCatalog
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    ContrabandItem,
    CredentialComponent,
    CredentialDefect,
    CredentialDefinition,
    CredentialStatus,
    CredentialToken,
    FailureClass,
    FailureMode,
    Indication,
    IndicationId,
    OriginId,
    RestrictionLevel,
    Restrictions,
    materialize_packet,
)
from .credentials_game import (
    CredentialCase,
    CredentialPresentationProfile,
    derive_defects,
)

# Contraband used by smuggling / relinquish failures when the intent itself
# carries none. Weapons are permit-gated (not anonymous) in the usual rule sets,
# so a declared one with no permit reads as a mitigatable infraction.
_DEFAULT_CONTRABAND = Indication.WEAPON


def build_valid(
    region: OriginId,
    purpose: IndicationId,
    restrictions: Restrictions,
    *,
    candidate_name: str = "Traveler",
    contraband: Sequence[IndicationId] = (),
    owner: object | None = None,
    catalog: TokenCatalog[CredentialDefinition] | None = None,
) -> CredentialCase:
    """Assemble a fully valid packet for ``purpose`` (+ declared contraband).

    The result derives to PASS under ``restrictions``. Declared contraband must be
    permittable; requesting a FORBIDDEN possession raises, since no valid packet
    can carry it (fail loud rather than return a non-valid case).
    """

    id_card: CredentialToken | None = None
    credentials: list[CredentialToken] = []
    possessions: list[ContrabandItem] = []
    level = restrictions.level_for(region, purpose, RestrictionLevel.ANONYMOUS)
    if level.requires_id:
        id_card = CredentialToken(indication=purpose, status=CredentialStatus.VALID)
    if level.requires_permit:
        credentials.append(
            CredentialToken(
                indication=purpose,
                status=CredentialStatus.VALID,
                requires_id=True,
            )
        )

    for c_ind in contraband:
        c_level = restrictions.level_for(region, c_ind, RestrictionLevel.FORBIDDEN)
        if c_level in (RestrictionLevel.CRIMINAL, RestrictionLevel.FORBIDDEN):
            raise ValueError(
                f"Cannot build a valid case with criminal/forbidden contraband: "
                f"{c_ind} in {region}."
            )
        if c_level.requires_permit:
            credentials.append(
                CredentialToken(
                    indication=c_ind,
                    status=CredentialStatus.VALID,
                    requires_id=True,
                )
            )
        possessions.append(ContrabandItem(indication=c_ind, concealed=False))

    return CredentialCase(
        candidate_name=candidate_name,
        presented_documents={},
        hidden_facts={},
        packet_hidden_facts={},
        packet_manager=materialize_packet(
            owner=owner or object(),
            region=region,
            purpose=purpose,
            id_card=id_card,
            credentials=credentials,
            possessions=possessions,
            label_prefix=candidate_name,
            catalog=catalog,
        ),
    )


def _purpose_permit(case: CredentialCase) -> CredentialComponent | None:
    return next(
        (
            component
            for component in case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT)
            if component.indication == case.get_purpose()
        ),
        None,
    )


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
            return bool(case.packet_manager.get_slot(CREDENTIAL_ID_SLOT))
        case FailureMode.UNPERMITTED_CONTRABAND | FailureMode.CONCEALED_CONTRABAND:
            return True
    return False


def apply_failure(mode: FailureMode, case: CredentialCase) -> None:
    """Mutate ``case`` in place to exhibit ``mode``. No-op if not applicable."""

    permit = _purpose_permit(case)
    match mode:
        case FailureMode.MISSING_PERMIT:
            if permit is not None:
                case.packet_manager.unassign(CREDENTIAL_PACKET_SLOT, permit)
        case FailureMode.UNSEALED_PERMIT:
            if permit is not None:
                permit.status = CredentialStatus.MISSING_SEAL
        case FailureMode.FORGED_PERMIT:
            if permit is not None:
                permit.status = CredentialStatus.FORGED
        case FailureMode.WRONG_HOLDER_PERMIT:
            if permit is not None:
                permit.subject_id = case.packet_manager.materialize_subject(
                    f"{case.candidate_name}:permit-subject"
                ).uid
        case FailureMode.MISSING_ID | FailureMode.EXPIRED_ID | FailureMode.FAKE_ID:
            id_components = case.packet_manager.get_slot(CREDENTIAL_ID_SLOT)
            if id_components:
                id_component = id_components[0]
                if mode is FailureMode.MISSING_ID:
                    case.packet_manager.unassign(CREDENTIAL_ID_SLOT, id_component)
                elif mode is FailureMode.EXPIRED_ID:
                    id_component.status = CredentialStatus.EXPIRED
                else:
                    subject_id = case.packet_manager.materialize_subject(
                        f"{case.candidate_name}:id-subject"
                    ).uid
                    id_component.subject_id = subject_id
                    for component in case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT):
                        if component.requires_id:
                            component.subject_id = subject_id
        case FailureMode.UNPERMITTED_CONTRABAND:
            case.packet_manager.possessions.append(
                ContrabandItem(indication=_DEFAULT_CONTRABAND, concealed=False)
            )
        case FailureMode.CONCEALED_CONTRABAND:
            case.packet_manager.possessions.append(
                ContrabandItem(indication=_DEFAULT_CONTRABAND, concealed=True)
            )


def degrade(case: CredentialCase, modes: Iterable[FailureMode]) -> CredentialCase:
    """Apply each failure mode to ``case`` in place and return it."""

    for mode in modes:
        apply_failure(mode, case)
    return case


def render_narrative(
    case: CredentialCase,
    defects: list[CredentialDefect],
) -> CredentialCase:
    """Render the default profile from one already-derived defect list."""

    return CredentialPresentationProfile().render_case(case, defects)


def make_case(
    region: OriginId,
    purpose: IndicationId,
    restrictions: Restrictions,
    *,
    failure_modes: Sequence[FailureMode] = (),
    candidate_name: str = "Traveler",
    contraband: Sequence[IndicationId] = (),
    owner: object | None = None,
    catalog: TokenCatalog[CredentialDefinition] | None = None,
) -> CredentialCase:
    """Tier 2 entry: build a valid packet, degrade it, and render its narrative."""

    case = build_valid(
        region,
        purpose,
        restrictions,
        candidate_name=candidate_name,
        contraband=contraband,
        owner=owner,
        catalog=catalog,
    )
    degrade(case, failure_modes)
    return render_narrative(case, derive_defects(case.packet_manager, restrictions))


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
