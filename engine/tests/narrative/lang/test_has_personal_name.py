import pydantic

from tangl.narrative.lang.has_personal_name import HasPersonalName

import pytest

# Mocking the IsGendered protocol
class Gendered(pydantic.BaseModel):
    is_xx: bool = False

GenderedPersonalName = pydantic.create_model("HasPersonalName", __base__ = (Gendered, HasPersonalName))

@pytest.fixture
def has_personal_name():
    return GenderedPersonalName(name="Jack", first_name="Jonathan", last_name="Smith")

def test_post_init(has_personal_name):
    assert has_personal_name.full_name == "Jonathan Smith"

def test_name(has_personal_name):
    assert has_personal_name.name == "Jack"

def test_title(has_personal_name):
    # setattr( has_personal_name, 'is_xx', False )
    assert has_personal_name.title == "Mr."
    has_personal_name.is_xx = True
    assert has_personal_name.is_xx is True
    assert has_personal_name.title == "Ms."

def test_titled_name(has_personal_name):
    assert has_personal_name.titled_name == "Mr. Smith"
    has_personal_name.is_xx = True
    assert has_personal_name.titled_name == "Ms. Smith"

def test_titled_full_name(has_personal_name):
    assert has_personal_name.titled_full_name == "Mr. Jonathan Smith"
    has_personal_name.is_xx = True
    assert has_personal_name.titled_full_name == "Ms. Jonathan Smith"

def test_akas(has_personal_name):
    has_personal_name._title = "Mr."
    expected = {"Jack", "Jonathan", "Smith", "Jonathan Smith", "Mr. Smith", "Mr. Jonathan Smith"}
    assert has_personal_name.akas() == expected

def test_goes_by(has_personal_name):
    assert has_personal_name.goes_by("Jonathan")
    assert not has_personal_name.goes_by("Jonny")
