"""
Credentials domain vocabulary and the opaque packet representation.

This module holds the theme-neutral derivation vocabulary -- ``Region``,
``Indication``, ``RestrictionLevel``, ``CredentialStatus`` -- and the lean value
types that back a candidate's credential packet (``CredentialToken``,
``ContrabandItem``).

The packet is meant to be **opaque to the game loop**: the loop and
``derive_disposition`` ask the candidate questions through a small discovery API
(see :class:`~tangl.mechanics.games.credentials_game.CredentialCase`) about
content, declared intent, and validity. Whether those answers are backed by
these flat enums (today) or by a richer Singleton token catalog with per-roster
media (later, see ``CREDENTIALS_LOOP_DESIGN.md`` A.6) is an implementation detail
behind that surface.

See also: ``CREDENTIALS_LOOP_DESIGN.md`` -- "The rule and failure-mode model".
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, TypeAlias
from uuid import UUID

from pydantic import Field

from tangl.core.bases import BaseModelPlus


class Region(str, Enum):
    """Candidate origin; selects which restriction map applies."""

    LOCAL = "local"
    FOREIGN_EAST = "foreign_east"  # typically allied
    FOREIGN_WEST = "foreign_west"  # typically hostile

    def __str__(self) -> str:
        return self.value


class Indication(str, Enum):
    """A reason a candidate may require a credential.

    Purpose indications (every candidate has one) and contraband indications
    (optional possessions) share one enum so the restriction map keys are
    uniform.
    """

    # purpose
    TRAVEL = "travel"
    WORK = "work"
    EMIGRATE = "emigrate"
    # contraband
    WEAPON = "weapon"
    DRUGS = "drugs"
    SECRETS = "secrets"

    def __str__(self) -> str:
        return self.value


OriginId: TypeAlias = Region | str
IndicationId: TypeAlias = Indication | str


PURPOSES: frozenset[IndicationId] = frozenset(
    {Indication.TRAVEL, Indication.WORK, Indication.EMIGRATE}
)
CONTRABAND: frozenset[IndicationId] = frozenset(
    {Indication.WEAPON, Indication.DRUGS, Indication.SECRETS}
)


class RestrictionLevel(Enum):
    """How permissive the rule is for an indication, most to least restrictive.

    ``criminal -> forbidden -> with_permit (req id) -> with_id -> anonymous``. A
    day's authored rule change is a delta along this axis for some indication.

    ``criminal`` and ``forbidden`` differ for *contraband*: a forbidden good can
    be relinquished (declared -> deny, surrender -> pass), but a criminal good is
    a per-se crime -- mere possession arrests, and neither declaring nor
    surrendering it rescues. Which goods are criminal is per rule set: a
    permissive regime simply maps the same good down to a lower level.
    """

    CRIMINAL = "criminal"          # possession is itself a crime; always arrest
    FORBIDDEN = "forbidden"        # never; no valid credential exists
    WITH_PERMIT = "with_permit"    # requires a permit (which itself requires id)
    WITH_ID = "with_id"            # requires a valid bearer id
    ANONYMOUS = "anonymous"        # always allowed; no document needed

    @property
    def requires_permit(self) -> bool:
        return self is RestrictionLevel.WITH_PERMIT

    @property
    def requires_id(self) -> bool:
        return self in (RestrictionLevel.WITH_PERMIT, RestrictionLevel.WITH_ID)


class CredentialStatus(Enum):
    """Validity of a single presented credential (document or id).

    The split between *mitigatable* infractions (fixable in the moment -> deny if
    unfixed) and *crimes* (-> arrest) drives the derived disposition.
    """

    VALID = "valid"
    # mitigatable infractions
    MISSING_SEAL = "missing_seal"
    BAD_DATE = "bad_date"
    EXPIRED = "expired"
    # crimes
    FORGED = "forged"            # bad / fake seal
    WRONG_HOLDER = "wrong_holder"  # compatibility input; compiles to subject bindings

    @property
    def is_valid(self) -> bool:
        return self is CredentialStatus.VALID

    @property
    def is_crime(self) -> bool:
        return self in (CredentialStatus.FORGED, CredentialStatus.WRONG_HOLDER)


class FailureClass(Enum):
    """How severe a packet failure is, and therefore the disposition it forces."""

    MITIGATABLE = "mitigatable"  # fixable in the moment -> deny if unfixed
    CRIME = "crime"              # -> arrest


class CredentialDefectKind(Enum):
    """The normalized kinds of a transient credential assessment.

    Why
    ---
    Policy and rendering need one semantic vocabulary instead of separate status
    interpretations.

    Key Features
    ------------
    Covers evidence, subject, intent, and possession violations without
    embedding world prose or disposition state.

    API
    ---
    Used as :attr:`CredentialDefect.kind` by the credentials evaluator.

    Notes
    -----
    These values are derived from a packet and mediated findings; they are not
    persisted on the packet or game.

    See also
    --------
    :class:`CredentialDefect`, :class:`FailureClass`.
    """

    MISSING_EVIDENCE = "missing_evidence"
    INVALID_EVIDENCE = "invalid_evidence"
    FRAUDULENT_EVIDENCE = "fraudulent_evidence"
    SUBJECT_MISMATCH = "subject_mismatch"
    PROHIBITED_INTENT = "prohibited_intent"
    CRIMINAL_INTENT = "criminal_intent"
    UNAUTHORIZED_POSSESSION = "unauthorized_possession"
    UNDECLARED_POSSESSION = "undeclared_possession"
    CRIMINAL_POSSESSION = "criminal_possession"


class CredentialDefect(BaseModelPlus):
    """One derived, presentation-free credential assessment observation.

    Why
    ---
    Represents the evaluator's policy input without making a second packet state.

    Key Features
    ------------
    Carries a normalized kind, severity class, semantic subject, and optional
    indication, component source, and status cause for rendering.

    API
    ---
    Produced by ``derive_defects`` and folded by ``derive_disposition``; a
    presentation profile may use ``source_id`` and ``cause`` for wording.

    Notes
    -----
    This value is transient assessment output. It neither persists on a packet
    nor replaces game-owned mediated finding state.

    See also
    --------
    :class:`CredentialDefectKind`, :class:`FailureClass`.
    """

    kind: CredentialDefectKind
    failure_class: FailureClass
    subject: Literal["intent", "identity", "authorization", "possession"]
    indication: IndicationId | None = None
    source_id: UUID | None = None
    cause: CredentialStatus | None = None


class FailureMode(Enum):
    """A single way a packet can be degraded away from valid.

    Used by the candidate factory's ``degrade`` (Phase A.2) and, later, sampled
    by the roster generator (A.3). ``failure_class`` splits the modes that a
    mediation could clear (-> deny) from outright crimes (-> arrest).
    """

    # mitigatable
    MISSING_PERMIT = "missing_permit"
    UNSEALED_PERMIT = "unsealed_permit"
    MISSING_ID = "missing_id"
    EXPIRED_ID = "expired_id"
    UNPERMITTED_CONTRABAND = "unpermitted_contraband"
    # crimes
    FORGED_PERMIT = "forged_permit"
    FAKE_ID = "fake_id"
    WRONG_HOLDER_PERMIT = "wrong_holder_permit"
    CONCEALED_CONTRABAND = "concealed_contraband"

    @property
    def failure_class(self) -> FailureClass:
        return FailureClass.CRIME if self in _CRIME_MODES else FailureClass.MITIGATABLE


_CRIME_MODES = frozenset(
    {
        FailureMode.FORGED_PERMIT,
        FailureMode.FAKE_ID,
        FailureMode.WRONG_HOLDER_PERMIT,
        FailureMode.CONCEALED_CONTRABAND,
    }
)


class CredentialToken(BaseModelPlus):
    """A single presented credential.

    ``holder_matches`` is accepted only at the factory compatibility boundary.
    Packet materialization turns it into a distinct component ``subject_id``;
    runtime assessment compares those subject references instead of consulting
    this value.
    """

    indication: IndicationId
    status: CredentialStatus = CredentialStatus.VALID
    requires_id: bool = False
    holder_matches: bool = True
    definition_ref: str | None = None


class ContrabandItem(BaseModelPlus):
    """A possession that may need a waiver, be relinquished, or be concealed."""

    indication: IndicationId
    concealed: bool = False
    permit: CredentialToken | None = None


# Authored as a nested map for convenience...
RestrictionMap = dict[IndicationId, RestrictionLevel]


class RestrictionRule(BaseModelPlus):
    """One rule: indication X from region R sits at restriction level L."""

    region: OriginId
    indication: IndicationId
    level: RestrictionLevel


class Restrictions(BaseModelPlus):
    """The day's rules, stored as a flat rule list.

    A flat list (rather than a ``dict[Region, dict[Indication, RestrictionLevel]]``)
    keeps the persisted game state JSON-serializable -- enum *dict keys* are not,
    and the VM hashes node state with ``json.dumps``. Author via :meth:`from_map`
    for the convenient nested-dict form; look rules up via :meth:`level_for`.
    """

    rules: list[RestrictionRule] = Field(default_factory=list)
    default_level: RestrictionLevel = RestrictionLevel.ANONYMOUS

    def level_for(
        self,
        region: OriginId,
        indication: IndicationId,
        default: RestrictionLevel | None = None,
    ) -> RestrictionLevel:
        for rule in self.rules:
            if rule.region == region and rule.indication == indication:
                return rule.level
        return default if default is not None else self.default_level

    @classmethod
    def from_map(
        cls,
        mapping: dict[OriginId, RestrictionMap],
        *,
        default_level: RestrictionLevel = RestrictionLevel.ANONYMOUS,
    ) -> Restrictions:
        return cls(
            rules=[
                RestrictionRule(region=region, indication=indication, level=level)
                for region, sub in mapping.items()
                for indication, level in sub.items()
            ],
            default_level=default_level,
        )


COMMON_LOCAL_RESTRICTIONS: RestrictionMap = {
    Indication.TRAVEL: RestrictionLevel.WITH_ID,
    Indication.WORK: RestrictionLevel.WITH_PERMIT,
    Indication.EMIGRATE: RestrictionLevel.WITH_PERMIT,
    Indication.WEAPON: RestrictionLevel.WITH_PERMIT,
    Indication.DRUGS: RestrictionLevel.FORBIDDEN,
    Indication.SECRETS: RestrictionLevel.FORBIDDEN,
}

COMMON_ALLIED_RESTRICTIONS: RestrictionMap = {
    Indication.TRAVEL: RestrictionLevel.WITH_ID,
    Indication.WORK: RestrictionLevel.WITH_PERMIT,
    Indication.EMIGRATE: RestrictionLevel.WITH_PERMIT,
    Indication.WEAPON: RestrictionLevel.WITH_PERMIT,
    Indication.DRUGS: RestrictionLevel.FORBIDDEN,
    Indication.SECRETS: RestrictionLevel.WITH_PERMIT,
}

COMMON_HOSTILE_RESTRICTIONS: RestrictionMap = {
    Indication.TRAVEL: RestrictionLevel.WITH_PERMIT,
    Indication.WORK: RestrictionLevel.FORBIDDEN,
    Indication.EMIGRATE: RestrictionLevel.ANONYMOUS,  # asylum seekers
    Indication.WEAPON: RestrictionLevel.FORBIDDEN,
    Indication.DRUGS: RestrictionLevel.FORBIDDEN,
    Indication.SECRETS: RestrictionLevel.WITH_PERMIT,
}

DEFAULT_RESTRICTIONS: Restrictions = Restrictions.from_map(
    {
        Region.LOCAL: COMMON_LOCAL_RESTRICTIONS,
        Region.FOREIGN_EAST: COMMON_ALLIED_RESTRICTIONS,
        Region.FOREIGN_WEST: COMMON_HOSTILE_RESTRICTIONS,
    }
)
