from pydantic import Field

from tangl.type_hints import UniqueLabel
from tangl.scripting import BaseScriptItem
from tangl.story.actor import RoleScript
from .enums import CredStatus
from .credentials import HasCredentials, CredDisposition

from tangl.story.scene import BlockScript
ChallengeScript = BlockScript

class PurposesScript(BaseScriptItem):
    ...

class ContrabandScript(BaseScriptItem):
    ...

class CredentialTypeScript(BaseScriptItem):
    # id, ticket, permit for various requirements, "doctor's note", "travel pass", etc.

    has_seal: bool = True         # proof of issue,
    has_issued: bool = True       # almost always
    valid_period: int = 1         # 1 time unit
    has_expiry: bool = False      # may or may not be shown

    satisfies_indications: set[UniqueLabel] = Field(default_factory=set)
    requires_holder_id: bool = False

    satisfies_holder_id: bool = False
    has_biometrics: bool = False  # usually if it satisfies id


class CredCheckCandidateScript(RoleScript):
    # has casting ref/template/conditions
    purpose: PurposesScript = Field(PurposesScript)
    contraband: ContrabandScript = Field(ContrabandScript)
    expected_disposition: CredDisposition = None  # Will set randomly according to distribution for none
    credential_status: CredStatus = None          # Will set randomly according to expected distribution for none


class CredCheckChallenge(ChallengeScript):

    num_encounters: int = 5

    restrictions: dict[UniqueLabel, CredDisposition] = None
    # { locals: { purpose1: with_permit, purpose2: with_id }, foreign: { purpose1: forbidden, purpose2: with_id } }

    extras: dict[UniqueLabel, CredCheckCandidateScript]
    expected_disposition_ratio: dict[UniqueLabel, dict[CredDisposition, float]] = None
    # { local_extras1: { good: 1, bad: 1, neutral: 1}, foreign_extras2: { good: 2 } }

