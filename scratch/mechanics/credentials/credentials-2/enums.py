"""
Screening restrictions are described in terms of _restriction level_ given _region_ of candidate and _indication_.
"""
from __future__ import annotations

import random

from enum import Enum, Flag, auto
from typing import NewType

from tangl.utils.enum_utils import EnumUtils


class Indication(EnumUtils, Enum):
    """
    Reasons for requiring a permit:
    - all candidates have a purpose indication (Travel is the default)
    - an additional contraband indication is optional (None is the default)
    """
    TRAVEL = auto()
    WORK = auto()
    EMIGRATE = auto()

    WEAPON = auto()
    DRUGS = auto()
    SECRETS = auto()

IND = Indication


class RestrictionLevel(Enum):
    """
    Every candidate will have a purpose and therefore _may_ require some kind of credential.
    """
    ALLOWED = 1       # always
    WITH_TOKEN = 2    # anonymous bearer token
    WITH_ID = 3
    WITH_PERMIT = 4   # also req id
    FORBIDDEN = 5     # never, permit unavailable
    NONE = 6          # no such indications should be generated

RL = RestrictionLevel


RestrictionMap = NewType('RestrictionMap', dict[IND, RL])
# The RestrictionMap represents the currently expected credential packet for each indication

# Example of a simple restriction map with all levels
common_restrictions = {
    IND.TRAVEL: RL.ALLOWED,
    IND.WORK: RL.WITH_TOKEN,
    IND.EMIGRATE: RL.WITH_ID,

    IND.WEAPON: RL.WITH_PERMIT,
    IND.DRUGS: RL.FORBIDDEN,
    IND.SECRETS: RL.NONE
}


class RestrictionReqs(Enum):
    NONE = auto()
    ANY_CONTRABAND = auto()
    ANY_CREDENTIAL = auto()
    ANY_ID = auto()

    def get_pairs(self):
        """
        Returns the appropriate (Indication, RestrictionLevel) pairs based on the enum member.
        """
        if self == RestrictionReqs.NONE:
            return []
        elif self == RestrictionReqs.ANY_CONTRABAND:
            return [(ind, rl) for ind in [IND.WEAPON, IND.DRUGS, IND.SECRETS]
                    for rl in [RL.WITH_TOKEN, RL.WITH_ID, RL.WITH_PERMIT, RL.FORBIDDEN]]
        elif self == RestrictionReqs.ANY_CREDENTIAL:
            return [(ind, rl) for ind in Indication
                    for rl in [RL.WITH_TOKEN, RL.WITH_ID, RL.WITH_PERMIT]]
        elif self == RestrictionReqs.ANY_ID:
            return [(ind, rl) for ind in Indication
                    for rl in [RL.WITH_ID, RL.WITH_PERMIT]]
        else:
            return []

    def presentations(self) -> list:
        return Presentation.presentations_for_restriction_req()[self]

RRQ = RestrictionReqs


class Presentation(Enum):
    """
    There are only a few possible initial presentations:

    - blacklisted
    - forged or invalid credential (req any restriction)
    - possible hidden (search, req any contraband restriction)
    - possible unpermitted (relinquish, req any contraband restriction)
    - possible missing (produce, req any restriction)
    - possible wrong holder (verify id, req id restriction)
    - no problem
    - whitelisted

    Each _possible_ status can be cleared or converted to a violation status
    """

    # Criminal presentations (arrest)
    # -------------------------------
    BLACKLISTED = auto()          # wanted
    HIDDEN_CONTRABAND = auto()    # presents as possible hidden contraband, fails search
    WRONG_ID_HOLDER = auto()      # presents as possible wrong id holder, fails to verify id
    FORGED_CREDENTIAL = auto()    # bad seal

    # Invalid presentation (deny)
    # ---------------------------
    DECLINES_SEARCH = auto()            # presents as possible hidden contraband, refuses search
    DECLINES_RELINQUISH_CONTRABAND = auto()  # presents as possible unpermitted contraband, refuses to relinquish contraband
    DECLINES_ID_VERIFICATION = auto()   # presents as possible wrong id holder, declines to verify id
    MISSING_CREDENTIAL = auto()         # presents as possible missing credential, declines to produce credential
    INVALID_CREDENTIAL = auto()         # missing seal, expired, post-dated, holder mismatch

    # Invalid Credential sub-categories
    # MISSING_SEAL = auto()
    # BAD_ISSUE_DATE = auto()       # post-dated in future
    # EXPIRED = auto()
    # HOLDER_MISMATCH = auto()      # permit doesn't match valid id, req permit + id restriction

    # Valid presentations (allow)
    # ---------------------------
    POSSIBLE_HIDDEN_CONTRABAND = auto()       # will allow search
    POSSIBLE_UNPERMITTED_CONTRABAND = auto()  # will relinquish contraband
    POSSIBLE_WRONG_ID_HOLDER = auto()         # will verify id
    POSSIBLE_MISSING_CREDENTIAL = auto()      # will produce credential
    NO_PROBLEMS = auto()
    WHITELISTED = auto()

    def restriction_reqs(self) -> RestrictionReqs:
        return self.restriction_reqs_for_presentation()[self]

    @classmethod
    def restriction_reqs_for_presentation(cls) -> dict:
        # Reversing the mapping from the one defined above
        # reversed_mapping = {}
        # for req, presentations in cls.presentations_for_restriction_req().items():
        #     for presentation in presentations:
        #         reversed_mapping[presentation] = req
        # return reversed_mapping
        return { vv: k for k, v in cls.presentations_for_restriction_req().items() for vv in v }

    @classmethod
    def presentations_for_restriction_req(cls) -> dict:
        return {
            RRQ.ANY_CONTRABAND: [
                cls.HIDDEN_CONTRABAND,
                cls.DECLINES_SEARCH,
                cls.DECLINES_RELINQUISH_CONTRABAND,
                cls.POSSIBLE_HIDDEN_CONTRABAND,
                cls.POSSIBLE_UNPERMITTED_CONTRABAND
            ],
            RRQ.ANY_CREDENTIAL: [
                cls.FORGED_CREDENTIAL,
                cls.MISSING_CREDENTIAL,
                cls.INVALID_CREDENTIAL,
                cls.POSSIBLE_MISSING_CREDENTIAL
            ],
            RRQ.ANY_ID: [
                cls.WRONG_ID_HOLDER,
                cls.DECLINES_ID_VERIFICATION,
                cls.POSSIBLE_WRONG_ID_HOLDER
            ],
            RRQ.NONE: [
                cls.BLACKLISTED,
                cls.WHITELISTED,
                cls.NO_PROBLEMS
            ]
        }

    def outcomes(self) -> list:
        return Outcome.outcomes_for_presentation()[self]


class Outcome(Enum):

    ARREST = auto()
    DENY = auto()
    ALLOW = auto()

    def presentations(self):
        return self.presentations_for_outcome()[self]

    @classmethod
    def presentations_for_outcome(cls):
        return {
            cls.ARREST: [Presentation.BLACKLISTED,
                         Presentation.HIDDEN_CONTRABAND,
                         Presentation.FORGED_CREDENTIAL,
                         Presentation.WRONG_ID_HOLDER],
            cls.DENY:   [Presentation.DECLINES_SEARCH,
                         Presentation.DECLINES_RELINQUISH_CONTRABAND,
                         Presentation.DECLINES_ID_VERIFICATION,
                         Presentation.MISSING_CREDENTIAL,
                         Presentation.INVALID_CREDENTIAL],
            cls.ALLOW:  [Presentation.POSSIBLE_HIDDEN_CONTRABAND,
                         Presentation.POSSIBLE_UNPERMITTED_CONTRABAND,
                         Presentation.POSSIBLE_WRONG_ID_HOLDER,
                         Presentation.POSSIBLE_MISSING_CREDENTIAL,
                         Presentation.WHITELISTED,
                         Presentation.NO_PROBLEMS]
        }

    @classmethod
    def outcomes_for_presentation(cls):
        return { vv: k for k, v in cls.presentations_for_outcome().items() for vv in v }


class Region(Enum):
    """
    An additional layer of rule organization.

    Candidates may belong to a particular region, and each region may have its own rules, depending on the shifting political environment.
    """
    LOCAL = auto()
    FOREIGN_EAST = auto()  # perhaps an allied region
    FOREIGN_WEST = auto()  # perhaps a hostile region

RegionalRestrictionMaps = NewType('RegionalRestrictionMap', dict[Region, RestrictionMap])
# The RegionalRestrictionMap represents the active restriction map for candidates originating from each game region.

common_allied_region_restictions = {
        IND.TRAVEL: RL.WITH_ID,
        IND.WORK: RL.WITH_PERMIT,      # visitor work permit
        IND.EMIGRATE: RL.WITH_PERMIT,  # long-term émigrés
        IND.WEAPON: RL.WITH_PERMIT,
        IND.DRUGS: RL.FORBIDDEN,
        IND.SECRETS: RL.WITH_PERMIT    # diplomatic id
    }

common_hostile_region_restrictions = {
        IND.TRAVEL: RL.WITH_PERMIT,    # travel permit
        IND.WORK: RL.FORBIDDEN,
        IND.EMIGRATE: RL.WITH_TOKEN,   # asylum seekers
        IND.WEAPON: RL.FORBIDDEN,
        IND.DRUGS: RL.FORBIDDEN,
        IND.SECRETS: RL.WITH_PERMIT    # diplomatic id
    }

common_regional_restrictions = {
    Region.LOCAL: common_restrictions,
    Region.FOREIGN_EAST: common_allied_region_restictions,
    Region.FOREIGN_WEST: common_hostile_region_restrictions
}
