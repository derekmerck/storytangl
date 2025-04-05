from enum import Enum

import pytest

from tangl.narrative.lang.personal_name import PersonalName, Gender

@pytest.fixture
def full_name():
    return PersonalName(
        given_name="Jonathan",
        middle_name="Quincy",
        family_name="Smith",
        title="Mr.",
        suffix="Jr.",
        nickname="Jack",
        gender=Gender.XY
    )

def test_from_full_name():
    name = PersonalName.from_full_name("Dr. Jane Marie Doe")
    assert name.given_name == "Jane"
    assert name.middle_name == "Marie"
    assert name.family_name == "Doe"
    assert name.title == "Dr."

def test_is_xx():
    name_xx = PersonalName(gender=Gender.XX)
    name_xy = PersonalName(gender=Gender.XY)
    assert name_xx.is_xx() is True
    assert name_xx.is_xx(Gender.XY) is False
    assert name_xy.is_xx() is False
    assert name_xx.is_xx(Gender.XX) is True

def test_get_title(full_name):
    assert full_name.get_title() == "Mr."
    assert full_name.get_title(Gender.XX) == "Ms."

def test_name(full_name):
    assert full_name.name() == "Jonathan"

def test_familiar_name(full_name):
    assert full_name.familiar_name() == "Jack"

def test_formal_name(full_name):
    assert full_name.formal_name() == "Mr. Smith"

def test_full_name(full_name):
    assert full_name.full_name() == "Jonathan Smith"

def test_familiar_full_name(full_name):
    assert full_name.familiar_full_name() == "Jack Smith"

def test_formal_full_name(full_name):
    assert full_name.formal_full_name() == "Mr. Jonathan Smith Jr."

def test_akas(full_name):
    expected_akas = {"Jonathan", "Smith", "Jack", "Jack Smith", "Jonathan Smith", "Mr. Smith", "Mr. Jonathan Smith Jr."}
    assert full_name.akas() == expected_akas

def test_goes_by(full_name):
    assert full_name.goes_by("Jack") is True
    assert full_name.goes_by("Johnny") is False

def test_missing_names():
    name = PersonalName()
    with pytest.raises(ValueError):
        name.familiar_name()
    with pytest.raises(ValueError):
        name.formal_name()

def test_normalize_gn():
    name = PersonalName(title="king", gender=Gender.XX)
    assert name.get_title() == "Queen"

def test_gender_flexibility():
    assert PersonalName(gender=Gender.XX).is_xx() is True
    assert PersonalName(gender="xx").is_xx() is True
    assert PersonalName(gender="XX").is_xx() is True
    assert PersonalName(gender="xy").is_xx() is False

    class OtherGender(Enum):
        MALE = "xy"
        FEMALE = "xx"

    assert PersonalName(gender=OtherGender.FEMALE).is_xx() is True
    assert PersonalName(gender=OtherGender.MALE).is_xx() is False

def test_invalid_gender():

    with pytest.raises(ValueError):
        invalid_name = PersonalName(gender="invalid")

def test_gender_in_get_title():
    name = PersonalName(title="king", gender=Gender.XY)
    assert name.get_title() == "King"
    assert name.get_title(Gender.XX) == "Queen"
    assert name.get_title("xx") == "Queen"

    with pytest.raises(ValueError):
        assert name.get_title("invalid") == "King"
