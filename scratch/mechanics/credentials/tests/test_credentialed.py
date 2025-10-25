import pytest

from tangl.graph import Node
from tangl.mechanics.credentials.credential_packet import Credentialed, IdCard, Outcome, Presentation, CS, Indication, Region

class CredentialedNode(Credentialed, Node):
    pass

# Trivial tests

@pytest.mark.xfail(reason="needs refactored")
def test_credential_packet_generation():
    candidate = CredentialedNode(
        region=Region.LOCAL,
        purpose=Indication.TRAVEL,
        contraband=None,
        expected_outcome=Outcome.ALLOW,
        presentation=Presentation.NO_PROBLEMS,
        credential_status=CS.VALID
    )
    assert candidate.credentials == set()
    assert isinstance(candidate.id_card, IdCard)
    assert candidate.id_card_info() == {
        'holder_name': candidate.full_name,
        'holder_id': candidate.id_card_number,
        'holder_text': candidate.id_card_text,
        'holder_photo': candidate.id_card_photo
    }

def test_expected_outcome():
    candidate = CredentialedNode(
        region=Region.LOCAL,
        purpose=Indication.TRAVEL,
        contraband=None,
        expected_outcome=Outcome.ALLOW,
        presentation=Presentation.NO_PROBLEMS,
        credential_status=CS.VALID
    )
    assert candidate.expected_outcome == Outcome.ALLOW

def test_presentation():
    candidate = CredentialedNode(
        region=Region.LOCAL,
        purpose=Indication.TRAVEL,
        contraband=None,
        expected_outcome=Outcome.ALLOW,
        presentation=Presentation.NO_PROBLEMS,
        credential_status=CS.VALID
    )
    assert candidate.presentation == Presentation.NO_PROBLEMS

def test_credential_status():
    candidate = CredentialedNode(
        region=Region.LOCAL,
        purpose=Indication.TRAVEL,
        contraband=None,
        expected_outcome=Outcome.ALLOW,
        presentation=Presentation.NO_PROBLEMS,
        credential_status=CS.VALID
    )
    assert candidate.credential_status == CS.VALID
