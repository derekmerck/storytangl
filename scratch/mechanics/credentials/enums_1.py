
from enum import Enum, auto

class CredDisposition(Enum):
    PASS   = auto()
    DENY   = auto()
    DETAIN = auto()

class CredStatus(Enum):

    # Pass
    OK = auto()
    POSSIBLE_MISSING = auto()     # presents as MISSING, mitigate by producing missing
    POSSIBLE_PROHIBITED = auto()  # presents as PROHIBITED, mitigate by search or relinquish
    WHITELISTED = auto()          # may present as INVALID, MISSING, PROHIBITED

    # Deny
    INVALID = auto()              # wrong cred date, type or missing seal, mitigate by crime
    MISSING = auto()              # missing id, ticket, or permit, mitigate by crime
    PROHIBITED = auto()           # declines search or relinquish, mitigate by crime

    # Detain or Deny
    FORGED = auto()               # wrong seal, mitigate by crime
    BLACKLISTED = auto()          # presents as OK, mitigate by crime
