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

from pydantic import Field

from tangl.core.bases import BaseModelPlus


class Region(Enum):
    """Candidate origin; selects which restriction map applies."""

    LOCAL = "local"
    FOREIGN_EAST = "foreign_east"  # typically allied
    FOREIGN_WEST = "foreign_west"  # typically hostile


class Indication(Enum):
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


PURPOSES = frozenset({Indication.TRAVEL, Indication.WORK, Indication.EMIGRATE})
CONTRABAND = frozenset({Indication.WEAPON, Indication.DRUGS, Indication.SECRETS})


class RestrictionLevel(Enum):
    """How permissive the rule is for an indication, most to least restrictive.

    ``forbidden -> with_permit (req id) -> with_id -> anonymous``. A day's
    authored rule change is a delta along this axis for some indication.
    """

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
    WRONG_HOLDER = "wrong_holder"  # fake or mismatched id

    @property
    def is_valid(self) -> bool:
        return self is CredentialStatus.VALID

    @property
    def is_crime(self) -> bool:
        return self in (CredentialStatus.FORGED, CredentialStatus.WRONG_HOLDER)


class CredentialToken(BaseModelPlus):
    """A single presented credential.

    ``holder_matches`` models the id-linkage surface for permits: a permit may be
    intrinsically valid yet reference a different bearer than the presented id (a
    crime), independent of the permit's own ``status``.
    """

    indication: Indication
    status: CredentialStatus = CredentialStatus.VALID
    requires_id: bool = False
    holder_matches: bool = True


class ContrabandItem(BaseModelPlus):
    """A possession that may need a waiver, be relinquished, or be concealed."""

    indication: Indication
    concealed: bool = False
    permit: CredentialToken | None = None


# Authored as a nested map for convenience...
RestrictionMap = dict[Indication, RestrictionLevel]


class RestrictionRule(BaseModelPlus):
    """One rule: indication X from region R sits at restriction level L."""

    region: Region
    indication: Indication
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
        region: Region,
        indication: Indication,
        default: RestrictionLevel | None = None,
    ) -> RestrictionLevel:
        for rule in self.rules:
            if rule.region is region and rule.indication is indication:
                return rule.level
        return default if default is not None else self.default_level

    @classmethod
    def from_map(
        cls,
        mapping: dict[Region, RestrictionMap],
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
