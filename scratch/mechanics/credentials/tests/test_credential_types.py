import logging

from tangl.mechanics.credentials.credential import *
from tangl.mechanics.credentials.enums import Indication, Region

import pytest

@pytest.fixture(autouse=True)
def credential_keys():
    logging.debug(list(CredentialType._instances.keys()))


def test_credentials_loaded():
    assert len( CredentialType._instances ) >= 9

def test_anon_travel_permit():
    permit = Credential("ticket")
    assert permit.valid_period == 0
    assert permit.indication is Indication.TRAVEL
    # assert permit.base_image is None

def test_anon_emigration_permit():
    permit = Credential("asylum")
    assert permit.valid_period == 30
    assert permit.indication is Indication.EMIGRATE
    # assert permit.base_image is None

def test_work_permit():
    permit = Credential("work_permit")
    assert permit.indication == Indication.WORK

def test_emigration_permit():
    permit = Credential("emigration_permit")
    assert permit.valid_period == 1000
    assert permit.indication is Indication.EMIGRATE


def test_weapon_permit():
    permit = Credential('weapon_permit')
    assert permit.indication is Indication.WEAPON

def test_drug_permit():
    permit = Credential('medical_id')
    assert permit.indication is Indication.DRUGS

def test_secret_permit():
    permit = Credential('diplomatic_id')
    assert permit.indication is Indication.SECRETS

@pytest.mark.skip(reason="broken")
def test_id_card():
    holder = Node()
    holder.region = Region.LOCAL
    card = IdCard(parent=holder)
    assert card.valid_period == 300
    assert isinstance(card.issuer, Region)
    assert card.holder.region == card.issuer

@pytest.mark.skip(reason="broken")
def test_permit():
    holder = Node()
    holder.id_card_number = "abcd-1234"
    permit = Permit(parent=holder)
    assert permit.valid_period == 100
    assert permit.req_id is True
    assert "holder_id" in permit.render()


