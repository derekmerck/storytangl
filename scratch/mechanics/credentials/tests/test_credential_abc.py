import pytest
from tangl.mechanics.credentials import Credential
from tangl.mechanics.credentials.enums import Region, Indication
from tangl.mechanics.credentials.credential import Seal, CS
from tangl.mechanics.credentials.journal_models import JournalCredential

# todo: parameterize this to iterate over all credential types

def test_credential_init():
    credential = Credential("ticket")
    assert credential.credential_status == CS.VALID
    assert credential.issuer == Region.LOCAL
    assert isinstance(credential.issued_turn, int)

def test_credential_properties():
    credential = Credential("ticket")
    assert isinstance(credential.expiry_turn, int)
    assert isinstance(credential.seal, Seal)

@pytest.mark.xfail(reason="need to refactor")
def test_credential_render():
    credential = Credential("ticket")
    result = credential.render()
    assert isinstance(result, dict)
    response = JournalCredential(**result)

    # assert "credential_type" in result
    # assert "credential_id" in result
    # assert "issuer" in result
    # assert "seal_image" in result
    # assert "base_image" in result
    # assert "issued" in result
    #
    # if credential.valid_period > 0:
    #     assert "expiry" in result
    # if credential.req_id:
    #     assert "holder_id" in result

def test_seal_type_for():
    seal = Seal.type_for(Region.LOCAL, Indication.TRAVEL, CS.VALID)
    assert seal is Seal.LOCAL_TRAVEL

    seal = Seal.type_for(Region.FOREIGN_EAST, Indication.SECRETS, CS.BAD_ISSUE_DATE)
    assert seal is Seal.FOREIGN_EAST_SECRETS

    seal = Seal.type_for(Region.FOREIGN_WEST, Indication.WORK, CS.BAD_SEAL)
    assert seal is Seal.FAKE_FOREIGN_WEST

# def test_credential_status_enum():
#     assert CredentialStatus.WRONG_SEAL in CredentialStatus.WRONG_SEAL
#     assert CredentialStatus.WRONG_ID_HOLDER in CredentialStatus.CRIME
#     assert CredentialStatus.MISSING_SEAL in CredentialStatus.
#
# def test_credential_status_enum_combinations():
#     assert CredentialStatus.MISSING_ID | CredentialStatus.MISSING_PERMIT == CredentialStatus.MISSING_CREDENTIAL
#     assert CredentialStatus.BAD_CREDENTIAL | CredentialStatus.MISSING_CREDENTIAL == CredentialStatus.INVALID
