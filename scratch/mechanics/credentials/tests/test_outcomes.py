from pprint import pprint

import pytest

from tangl.mechanics.credentials.enums import Outcome, Presentation
from tangl.mechanics.credentials.outcomes_graph import build_graph

def test_outcome_presentations():
    assert set(Outcome.ALLOW.presentations()) == {
        Presentation.WHITELISTED,
        Presentation.NO_PROBLEMS,
        Presentation.POSSIBLE_HIDDEN_CONTRABAND,
        Presentation.POSSIBLE_UNPERMITTED_CONTRABAND,
        Presentation.POSSIBLE_WRONG_ID_HOLDER,
        Presentation.POSSIBLE_MISSING_CREDENTIAL
    }
    assert set(Outcome.ARREST.presentations()) == {
        Presentation.BLACKLISTED,
        Presentation.HIDDEN_CONTRABAND,
        Presentation.FORGED_CREDENTIAL,
        Presentation.WRONG_ID_HOLDER
    }
    assert set(Outcome.DENY.presentations()) == {
        Presentation.DECLINES_RELINQUISH_CONTRABAND,
        Presentation.DECLINES_SEARCH,
        Presentation.DECLINES_ID_VERIFICATION,
        Presentation.MISSING_CREDENTIAL,
        Presentation.INVALID_CREDENTIAL
    }

# def test_presentation_credential_statuses():
#     assert Presentation.FORGED_CREDENTIAL.get_credential_statuses() == [CS.WRONG_SEAL]
#     assert Presentation.WRONG_ID_HOLDER.get_credential_statuses() == [CS.WRONG_ID_HOLDER]
#     assert Presentation.INVALID_CREDENTIAL.get_credential_statuses() == list(CS.MISSING_SEAL, CS.MIS)
#     assert Presentation.MISSING_CREDENTIAL.get_credential_statuses() == list(CS.MISSING_CREDENTIAL)
#     assert Presentation.POSSIBLE_UNPERMITTED_CONTRABAND.get_credential_statuses() == [CS.MISSING_PERMIT]
#     assert Presentation.NO_PROBLEMS.get_credential_statuses() == CS.NO_PROBLEMS
#     assert Presentation.WHITELISTED.get_credential_statuses() == CS.NO_PROBLEMS



