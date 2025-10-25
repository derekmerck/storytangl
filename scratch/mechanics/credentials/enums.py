from __future__ import annotations
from enum import Enum, auto, Flag

class Region(Enum):
    """High-level candidate class membership"""
    LOCAL = auto()
    FOREIGN_EAST = auto()
    FOREIGN_WEST = auto()

class Indication(Flag):
    """
    Possible reason for requiring a permit
    - all candidates have a purpose indication (travel is the default)
    - a contraband indication is optional (None is the default)
    """
    TRAVEL = auto()
    WORK = auto()
    EMIGRATE = auto()
    PURPOSE = TRAVEL | WORK | EMIGRATE

    WEAPON = auto()
    DRUGS = auto()
    SECRETS = auto()
    CONTRABAND = WEAPON | DRUGS | SECRETS

class Seal(Enum):
    # Various legitimizing or fake seals for credentials
    LOCAL = auto()

    LOCAL_TRAVEL = auto()
    LOCAL_WORK = auto()
    LOCAL_EMIGRATION = auto()

    LOCAL_WEAPONS = auto()
    LOCAL_DRUGS = auto()
    LOCAL_SECRETS = auto()

    FOREIGN_EAST = auto()
    FOREIGN_EAST_SECRETS = auto()

    FOREIGN_WEST = auto()
    FOREIGN_WEST_SECRETS = auto()

    # errors
    NONE = auto()
    FAKE_LOCAL = auto()
    FAKE_FOREIGN_EAST = auto()
    FAKE_FOREIGN_WEST = auto()

    @classmethod
    def type_for(cls,
                 region: Region,
                 indication: Indication,
                 valid: bool) -> 'Seal':
        # which seal to use for a given region and indication, both legitimate and invalid
        match region, indication, valid:
            case Region.LOCAL, _, False:
                return Seal.FAKE_LOCAL
            case Region.LOCAL, Indication.TRAVEL, _:
                return Seal.LOCAL_TRAVEL
            case Region.LOCAL, Indication.WORK, _:
                return Seal.LOCAL_WORK
            case Region.LOCAL, Indication.EMIGRATE, _:
                return Seal.LOCAL_EMIGRATION
            case Region.LOCAL, Indication.WEAPON, _:
                return Seal.LOCAL_WEAPONS
            case Region.LOCAL, Indication.DRUGS, _:
                return Seal.LOCAL_DRUGS
            case Region.LOCAL, Indication.SECRETS, _:
                return Seal.LOCAL_SECRETS
            case Region.LOCAL, _, _:
                return Seal.LOCAL

            case Region.FOREIGN_EAST, _, False:
                return Seal.FAKE_FOREIGN_EAST
            case Region.FOREIGN_EAST, Indication.SECRETS, _:
                return Seal.FOREIGN_EAST_SECRETS
            case Region.FOREIGN_EAST, _, _:
                return Seal.FOREIGN_EAST

            case Region.FOREIGN_WEST, _, False:
                return Seal.FAKE_FOREIGN_WEST
            case Region.FOREIGN_WEST, Indication.SECRETS, _:
                return Seal.FOREIGN_WEST_SECRETS
            case Region.FOREIGN_WEST, _, _:
                return Seal.FOREIGN_WEST
        raise TypeError(f"No seal could be determined for {region}, {indication}, {valid}")


class Move(Enum):
    """
    The 'Move' enum describes all possible game interactions for a round.
      - Some inspect actions require an additional parameter for the specific credential inspected
      - Inspect actions may change the round justification state from Allow -> Deny or Crime
      - Req actions may clear a "possible" state to an actionable state
      - Side actions like AcceptToken have no effect on game state but may be used for flavor in the challenge framework.  They are included in this set for consistency in generating ChallengeActions.
      - Allow, Deny, or Arrest complete the round
    """

    # Inspect actions may change round outcome state

    # Inspect CR actions must be applied to a specific credential
    INSPECT_CR_SEAL = auto()               # check for MISSING_SEAL, BAD_SEAL (C)
    INSPECT_CR_ISSUER = auto()             # check for BAD_REGION
    INSPECT_CR_ISSUE_DATE = auto()         # check for BAD_DATE
    # Only if credential as expiry
    INSPECT_CR_EXPIRY = auto()             # check for EXPIRED
    # Only if credential has req_id
    INSPECT_CR_HOLDER_ID = auto()          # check for POSS_H_MISMATCH, POSS_MISS_ID (M)
    # Only if credential has holder_detail
    INSPECT_CR_HOLDER_DETAIL = auto()      # check for POSS_WRONG_ID_HOLDER (CM)

    INSPECT_PURPOSE = auto()               # check for POSS_MISS_PERMIT
    # Only if contraband is visible
    INSPECT_CONTRABAND = auto()            # check for POSS_MISS_PERMIT, FORBIDDEN_CONTRABAND (M)

    # Req actions
    REQ_VALIDATE_ID = auto()               # mediation for POSS_WRONG_ID_HOLDER
    REQ_MISSING_CREDENTIAL = auto()        # mediation for POSS_MISS_CRED
    REQ_RELINQUISH_CONTRABAND = auto()     # mediation for POSS_FORBIDDEN_CONTRABAND
    # Only if candidate is unsearched
    REQ_SEARCH = auto()                    # mediation for POSS_HIDDEN_CONTRABAND (CM)

    INSPECT_BLACKLIST = auto()             # check for BLACKLISTED (C)
    INSPECT_WHITELIST = auto()             # check for WHITELISTED, clears violations

    # side actions
    INTERACT = auto()
    CONFISCATE_CREDENTIALS = auto()     # deny
    ACCEPT_TOKEN = auto()               # accept a token or bribe
    GIVE_TOKEN = auto()                 # give a token or bribe

    # disposition decisions that finalize the round
    ALLOW = auto()
    DENY = auto()
    ARREST = auto()

    def appropriate_for(self, outcome: Outcome):
        match self, outcome:
            case Move.ARREST, x if x in Outcome.CRIME:
                return True
            case Move.DENY, x if x in Outcome.DENY:
                return True
            case Move.ALLOW, x if x in Outcome.ACCEPT:
                return True
            case Move.ALLOW | Move.DENY | Move.ARREST, _:
                return False
        raise TypeError(f"{outcome} is not a disposition")

class Outcome(Flag):
    """
    This is a hierarchical enumeration.  Higher order members like "DENY" are
    made up out of a set of lower order members like "BAD_CREDENTIAL".

    EnumUtils provides a "specify" function that will select a specific lower
    order member from a set.

    This allows creating candidates procedurally, either by passing in a specific
    infraction like "EXPIRED" or a general category like "DENY", which will
    automatically try to select an appropriate specific infraction.

    The expected outcome be _in_ the final action decision to be considered an appropriate response.
    """

    WRONG_SEAL = auto()
    FORGED_CREDENTIAL = WRONG_SEAL
    # wrong id holder presents as _possible_ wrong id holder, it can be changed to declined mediation/denied, but not cleared
    WRONG_ID_HOLDER = auto()
    # concealed contraband presents as _possible_ concealed contraband, can be changed to declined mediation/denied, but not cleared
    HIDDEN_CONTRABAND = auto()
    BLACKLISTED = WANTED = auto()

    CRIME = FORGED_CREDENTIAL | WRONG_ID_HOLDER | HIDDEN_CONTRABAND | BLACKLISTED

    MISSING_SEAL = auto()
    BAD_ISSUE_DATE = auto()
    EXPIRED = auto()
    HOLDER_MISMATCH = auto()
    BAD_CREDENTIAL = MISSING_SEAL | BAD_ISSUE_DATE | EXPIRED | HOLDER_MISMATCH

    # missing cred presents as possible missing cred, but cannot be cleared (candidate does not have required permit hidden, will not relinquish)
    MISSING_ID = auto()                # declines to produce to clear
    MISSING_PERMIT = auto()            # declines to produce or relinquish to clear
    MISSING_CREDENTIAL = MISSING_ID | MISSING_PERMIT

    # refuse validation presents as possible wrong id
    DECLINED_VALIDATE_ID = auto()
    # refuse search for contraband
    DECLINED_SEARCH = auto()         # this is special case that converts a candidate to deny status
    FORBIDDEN_CONTRABAND = auto()    # declines to relinquish to clear
    DECLINE_MEDIATION = DECLINED_VALIDATE_ID | FORBIDDEN_CONTRABAND | DECLINED_SEARCH

    DENY = BAD_CREDENTIAL | MISSING_CREDENTIAL | DECLINE_MEDIATION

    POSSIBLE_WRONG_ID_HOLDER = auto()       # clear with REQ_VALIDATE_ID
    POSSIBLE_MISSING_CREDENTIAL = auto()    # will clear with REQ_MISSING_CREDENTIAL or REQ_RELINQUISH_CONTRABAND (for missing contraband permit)
    POSSIBLE_FORBIDDEN_CONTRABAND = auto()  # will clear with REQ_RELINQUISH_CONTRABAND
    # this is irrelevant, always true until candidate is searched
    POSSIBLE_HIDDEN_CONTRABAND = auto()     # clear with REQ_SEARCH

    # mediations can be cleared to no_error, otherwise they are escalated to declined mediation
    MEDIATE = POSSIBLE_WRONG_ID_HOLDER | POSSIBLE_MISSING_CREDENTIAL | POSSIBLE_HIDDEN_CONTRABAND | POSSIBLE_FORBIDDEN_CONTRABAND

    WHITELISTED = auto()
    NO_ERROR = auto()

    ACCEPT = WHITELISTED | NO_ERROR | MEDIATE
