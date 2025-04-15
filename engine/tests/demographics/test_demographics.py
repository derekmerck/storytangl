import logging

import pytest

from tangl.mechanics.demographics import DemographicData, DemographicSampler
from tangl.mechanics.demographics.data_models import Region, Country, Subtype, NameBank
from tangl.narrative.lang.gens import Gens as Gender
from tangl.narrative.lang.age_range import AgeRange

@pytest.fixture(autouse=True)
def clear_singletons():
    Region.clear_instances()
    Country.clear_instances()
    Subtype.clear_instances()
    NameBank.clear_instances()


@pytest.fixture
def test_data():
    # Create test regions
    europe = Region(label="europe", name="Europe", demonym="European", eth_mix={'european': 1})
    asia = Region(label="asia", name="Asia", demonym="Asian", eth_mix={'asian': 1})

    # Create test countries
    france = Country(label="france", name="France", demonym="French", population=67000000)
    germany = Country(label="germany", name="Germany", demonym="German", population=83000000)
    japan = Country(label="japan", name="Japan", demonym="Japanese", population=126000000)
    #
    # Add countries to regions
    europe.countries.add(france)
    europe.countries.add(germany)
    asia.countries.add(japan)

    # Create test subtypes
    european = Subtype(label="european", name="European", demonym="European")
    asian = Subtype(label="asian", name="Asian", demonym="Asian")

    # Create test name banks
    french_names = NameBank(
        label="france",
        female=["Marie", "Sophie"],
        male=["Jean", "Pierre"],
        surname=["Dupont", "Durand"]
    )
    german_names = NameBank(
        label="germany",
        female=["Anna", "Maria"],
        male=["Hans", "Klaus"],
        surname=["Mueller", "Schmidt"]
    )
    japanese_names = NameBank(
        label="japan",
        female=["Yuki", "Aiko"],
        male=["Hiroshi", "Takeshi"],
        surname=["Tanaka", "Sato"]
    )
    #
    # # Associate name banks with countries and subtypes
    # france.name_bank() = french_names
    # germany.name_banks[german] = german_names
    # japan.name_banks[japanese] = japanese_names
    #
    # # Set up eth_mix for countries
    # france.eth_mix_ = {french: 1}
    # germany.eth_mix_ = {german: 1}
    # japan.eth_mix_ = {japanese: 1}
    #
    # # Set up eth_mix for regions
    # europe.eth_mix = {french: 1, german: 1}
    # asia.eth_mix = {japanese: 1}

    yield {
        "regions": [europe, asia],
        "countries": [france, germany, japan],
        "subtypes": [european, asian],
        "name_banks": [french_names, german_names, japanese_names]
    }

def test_namebank_singleton():
    nb1 = NameBank(label="test_bank", female=["Alice"], male=["Bob"], surname=["Smith"])
    nb2 = NameBank.get_instance("test_bank")
    assert nb1 is nb2


def test_country_namebank():
    country = Country(label="test_country", name="Test Country", demonym="Test", population=1000000)
    NameBank(label=country.label, female=["Eve"], male=["Charlie"], surname=["Johnson"])
    assert country.namebank().xx_names == ["Eve"]

    subtype = Subtype(label="test_subtype")
    NameBank(label=f"{country.label}_{subtype.label}", female=["Alice"], male=["Bob"], surname=["Smith"])
    assert country.namebank().xx_names == ["Eve"]

    print( country.namebank() )
    print( country.namebank('test_subtype'))
    print( list(NameBank._instances.items()) )

    assert country.namebank(subtype).xx_names == ["Alice"]
    # assert country.namebank(subtype.label).xx_names == ["Alice"]

    # ensure singleton subclasses hash
    { country.namebank() }
    { country.namebank(subtype) }

def test_region_eth_mix_validator():
    subtype = Subtype(label="test_subtype")
    region = Region(label="test_region", name="Test Region", demonym="Test", eth_mix={"test_subtype": 1})
    assert isinstance(list(region.eth_mix.keys())[0], Subtype)

def test_demographic_data_inheritance():
    demo_data = DemographicData(given_name="John", family_name="Doe")
    assert demo_data.name() == "John"
    assert demo_data.full_name() == "John Doe"

from pydantic import BaseModel
from tangl.mechanics.demographics.demographic import HasDemographic
class TestEntity(HasDemographic, BaseModel):
    pass

def test_has_demographic():
    demo_data = DemographicData(given_name="Jane", family_name="Smith")
    entity = TestEntity(demographic=demo_data)
    assert entity.name == "Jane"
    assert entity.full_name == "Jane Smith"

def test_age_range_sampling():
    age_range = DemographicSampler.sample_age_range()
    assert isinstance(age_range, AgeRange)

def test_region_sampling(test_data):
    region = DemographicSampler.sample_region()
    assert region in test_data["regions"]


def test_country_sampling(test_data):
    region = test_data["regions"][0]  # Europe
    country = DemographicSampler.sample_country(region)
    assert country in region.countries


def test_subtype_sampling(test_data):
    country = test_data["countries"][0]  # France
    subtype = DemographicSampler.sample_subtype(country)
    assert subtype in country.eth_mix


def test_gender_sampling():
    gender = DemographicSampler.sample_gender()
    assert gender in [Gender.XX, Gender.XY]


def test_name_sampling(test_data):
    country = test_data["countries"][0]  # France
    # subtype = list(country.name_banks.keys())[0]
    nb = NameBank.get_instance(country.label)
    gender = Gender.XX
    d = DemographicSampler.sample_demographic(country=country, gender=gender)
    assert d.given_name in nb.xx_names
    assert d.family_name in nb.surname


def test_demographic_sampling(test_data):
    demo_data = DemographicSampler.sample_demographic()
    assert isinstance(demo_data, DemographicData)
    assert demo_data.region in test_data["regions"]
    assert demo_data.country in demo_data.region.countries
    assert demo_data.subtype in demo_data.country.eth_mix
    assert demo_data.gender in [Gender.XX, Gender.XY]


def test_demographic_sampling_with_params(test_data):
    region = test_data["regions"][0]  # Europe
    country = test_data["countries"][0]  # France
    subtype = test_data["subtypes"][0]  # French
    gender = Gender.XX

    demo_data = DemographicSampler.sample_demographic(region=region, country=country, subtype=subtype, gender=gender)

    assert demo_data.region == region
    assert demo_data.country == country
    # assert demo_data.subtype == subtype
    assert demo_data.gender == gender


def test_demonym_property():
    demo_data = DemographicData(
        given_name="Test",
        family_name="User",
        region=Region(label="test_region", name="Test Region", demonym="Test Regional", eth_mix={}),
        country=Country(label="test_country", name="Test Country", demonym="Test National", population=1000000),
        subtype=Subtype(label="test_subtype", name="Test Subtype", demonym="Test Subtype")
    )

    assert demo_data.demonym == "Test Regional"

    demo_data.region = None
    assert demo_data.demonym == "Test National"

    demo_data.country = None
    logging.debug(demo_data.subtype)
    assert demo_data.demonym == "Test Subtype"

def test_full_demographic_sampling(test_data):
    demo = DemographicSampler.sample_demographic()
    assert isinstance(demo, DemographicData)
    assert demo.region is not None
    assert demo.country is not None
    assert demo.subtype is not None
    assert demo.gender is not None
    assert demo.age_range is not None
