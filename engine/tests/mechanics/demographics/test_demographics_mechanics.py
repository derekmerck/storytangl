"""
Test demographic sampling MECHANICS with minimal data.

These tests verify the logic of the sampling system works correctly.
They run even without LFS data by using stub demographics.
"""

import sys
from importlib import util
from pathlib import Path

import pytest

from tangl.lang.age_range import AgeRange
from tangl.lang.gens import Gens as Gender
from tangl.mechanics.demographics import DemographicData, DemographicSampler
from tangl.mechanics.demographics.data_models import Country, NameBank, Region, Subtype


@pytest.fixture(autouse=True)
def clear_and_reload_singletons():
    """Clear singletons before each test, then ensure minimal data exists."""
    Region.clear_instances()
    Country.clear_instances()
    Subtype.clear_instances()
    NameBank.clear_instances()

    _populate_stub_data_from_conftest()


def _populate_stub_data_from_conftest() -> None:
    """Load the shared stub-population helper without relying on package imports."""
    module = sys.modules.get("engine.tests.mechanics.demographics.conftest")
    if module is None:
        module = sys.modules.get("conftest")
    if module is None:
        spec = util.spec_from_file_location(
            "demographics_conftest", Path(__file__).with_name("conftest.py")
        )
        if spec is None or spec.loader is None:
            raise ImportError("Unable to load demographics conftest helper")
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[call-arg]

    module._populate_stub_data()  # type: ignore[attr-defined]


def test_namebank_singleton():
    """Test that NameBank singleton pattern works correctly."""
    nb1 = NameBank(label="test_bank", female=["Alice"], male=["Bob"], surname=["Smith"])
    nb2 = NameBank.get_instance("test_bank")
    assert nb1 is nb2


def test_country_namebank():
    """Test that countries can resolve their namebanks."""
    country = Country(label="test_country", name="Test Country", demonym="Test", population=1_000_000)
    NameBank(label=country.label, female=["Eve"], male=["Charlie"], surname=["Johnson"])
    assert country.namebank().xx_names == ["Eve"]

    subtype = Subtype(label="test_subtype")
    NameBank(label=f"{country.label}_{subtype.label}", female=["Alice"], male=["Bob"], surname=["Smith"])
    assert country.namebank().xx_names == ["Eve"]
    assert country.namebank(subtype).xx_names == ["Alice"]

    # ensure singleton subclasses hash
    {country.namebank()}
    {country.namebank(subtype)}


def test_region_eth_mix_validator():
    """Test that region ethnic mix properly converts labels to Subtype instances."""
    subtype = Subtype(label="test_subtype")
    region = Region(label="test_region", name="Test Region", demonym="Test", eth_mix={"test_subtype": 1})
    assert isinstance(list(region.eth_mix.keys())[0], Subtype)


def test_demographic_data_structure():
    """Test DemographicData basic structure."""
    demo_data = DemographicData(given_name="John", family_name="Doe")
    assert demo_data.name() == "John"
    assert demo_data.full_name() == "John Doe"


def test_age_range_sampling():
    """Test that age range sampling returns valid AgeRange."""
    age_range = DemographicSampler.sample_age_range()
    assert isinstance(age_range, AgeRange)


def test_region_sampling():
    """Test that region sampling returns a valid region."""
    region = DemographicSampler.sample_region()
    assert region in Region.all_instances()


def test_country_sampling():
    """Test that country sampling respects region constraints."""
    region = list(Region.all_instances())[0]
    country = DemographicSampler.sample_country(region)
    assert country in region.countries


def test_subtype_sampling():
    """Test that subtype sampling respects country ethnic mix."""
    country = list(Country.all_instances())[0]
    subtype = DemographicSampler.sample_subtype(country)
    assert subtype in country.eth_mix


def test_gender_sampling():
    """Test that gender sampling returns valid gender."""
    gender = DemographicSampler.sample_gender()
    assert gender in [Gender.XX, Gender.XY]


def test_name_sampling():
    """Test that name sampling pulls from correct namebank."""
    country = Country.get_instance("fra")  # stub data includes 'fra'
    nb = NameBank.get_instance(country.label)
    demo = DemographicSampler.sample_demographic(country=country, gender=Gender.XX)
    assert demo.given_name in nb.xx_names
    assert demo.family_name in nb.surname


def test_demographic_sampling_complete():
    """Test that full demographic sampling produces valid structure."""
    demo = DemographicSampler.sample_demographic()
    assert isinstance(demo, DemographicData)
    assert demo.region is not None
    assert demo.country is not None
    assert demo.country in demo.region.countries
    assert demo.subtype is not None
    assert demo.subtype in demo.country.eth_mix
    assert demo.gender in [Gender.XX, Gender.XY]
    assert demo.age_range is not None


def test_demonym_resolution():
    """Test that demonym property resolves correctly through hierarchy."""
    demo_data = DemographicData(
        given_name="Test",
        family_name="User",
        region=Region(label="test_region", name="Test Region", demonym="Test Regional", eth_mix={}),
        country=Country(label="test_country", name="Test Country", demonym="Test National", population=1_000_000),
        subtype=Subtype(label="test_subtype", name="Test Subtype", demonym="Test Subtype"),
    )

    assert demo_data.demonym == "Test Regional"

    demo_data.region = None
    assert demo_data.demonym == "Test National"

    demo_data.country = None
    assert demo_data.demonym == "Test Subtype"
