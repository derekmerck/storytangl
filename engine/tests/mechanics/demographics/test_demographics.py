"""Sampler and facet behavior with explicitly selected sample data."""
from __future__ import annotations

import logging
import random

import pytest
from pydantic import BaseModel, ValidationError
from tangl.core import TokenCatalog

from tangl.mechanics.demographics import (
    DemographicData,
    DemographicSampler,
    HasDemographics,
    NameForm, NamePart, NamePool,
)
from tangl.mechanics.demographics.data_models import Region, Country, Subtype, NameBank
from tangl.lang.gens import Gens as Gender
from tangl.lang.age_range import AgeRange
from tangl.lang.personal_name import PersonalName

@pytest.fixture(scope="module")
def test_data():
    from tangl.mechanics.demographics import load_pack, register_pack

    catalog = register_pack(load_pack("sample"))
    yield {
        "catalogs": [catalog],
        "regions": [Region.get_instance("west_europe"), Region.get_instance("asia")],
        "countries": [Country.get_instance("fra"), Country.get_instance("jpn")],
        "subtypes": [Subtype.get_instance("european"), Subtype.get_instance("asian")],
    }


def test_namebank_singleton():
    nb1 = NameBank(label="test_bank", forms={"plain": NameForm(
        given=NamePart(pool=NamePool(candidates=["Alice"])),
        family=NamePart(pool=NamePool(candidates=["Smith"])),
    )})
    nb2 = NameBank.get_instance("test_bank")
    assert nb1 is nb2


def test_country_namebank():
    country = Country(label="test_country", name="Test Country", demonym="Test", population=1000000)
    base = NameBank(label=country.label, forms={"plain": NameForm(
        given=NamePart(pool=NamePool(candidates=["Eve"])),
        family=NamePart(pool=NamePool(candidates=["Johnson"])),
    )})
    subtype = Subtype(label="test_subtype")
    exact = NameBank(label=f"{country.label}_{subtype.label}", forms={"plain": NameForm(
        given=NamePart(pool=NamePool(candidates=["Alice"])),
        family=NamePart(pool=NamePool(candidates=["Smith"])),
    )})
    catalogs = [TokenCatalog(NameBank, members=(base, exact))]
    assert country.namebank(catalogs=catalogs) is base
    assert country.namebank(subtype, catalogs=catalogs) is exact
    assert hash(country.namebank(subtype, catalogs=catalogs)) == hash(exact)


def test_region_retains_explicit_subtype_reference():
    subtype = Subtype(label="explicit_region_subtype")
    region = Region(label="explicit_region", name="Test Region", demonym="Test",
                    eth_mix={subtype: 1})
    assert next(iter(region.eth_mix)) is subtype

def test_demographic_data_is_profile_only():
    profile = DemographicData(gender=Gender.X_, age_range=AgeRange.ADULT)
    assert not isinstance(profile, PersonalName)
    assert profile.gender is Gender.X_
    assert profile.age_range is AgeRange.ADULT
    with pytest.raises(ValidationError):
        DemographicData(given_name="John", family_name="Doe")


class DemoEntity(HasDemographics, BaseModel):
    pass


def test_has_demographics_publishes_facts_without_name_shadowing():
    profile = DemographicData(gender=Gender.X_)
    entity = DemoEntity(demographic=profile)
    assert entity.get_ns()["demographic"] is profile
    assert entity.get_ns()["gender"] is Gender.X_
    assert "name" not in entity.get_ns()
    assert "full_name" not in entity.get_ns()


def test_age_range_sampling():
    age_range = DemographicSampler.sample_age_range()
    assert isinstance(age_range, AgeRange)

def test_region_sampling(test_data):
    region = DemographicSampler.sample_region()
    assert region in Region.all_instances()


def test_country_sampling(test_data):
    region = test_data["regions"][0]  # Europe
    country = DemographicSampler.sample_country(region)
    assert country in region.countries


def test_country_sampling_orders_region_countries_deterministically(test_data):
    region = test_data["regions"][0]  # Europe
    captured: dict[str, list[str]] = {}

    class SpyRandom:
        def choice(self, options):
            captured["labels"] = [country.label for country in options]
            return options[0]

    country = DemographicSampler.sample_country(region, weighted=False, rng=SpyRandom())

    assert captured["labels"] == sorted(country.label for country in region.countries)
    assert country.label == captured["labels"][0]


def test_subtype_sampling(test_data):
    country = test_data["countries"][0]  # France
    subtype = DemographicSampler.sample_subtype(country)
    assert subtype in country.eth_mix


def test_gender_sampling():
    gender = DemographicSampler.sample_gender()
    assert gender in [Gender.XX, Gender.XY]


def test_name_sampling(test_data):
    bank = NameBank.get_instance("fra")
    name = DemographicSampler.sample_name(
        bank, form="female", catalogs=test_data["catalogs"], rng=random.Random(7),
    )
    assert name.given_name in bank.forms["female"].given.pool.candidates
    assert name.family_name in bank.forms["female"].family.pool.candidates


def test_demographic_sampling(test_data):
    demo_data = DemographicSampler.sample_demographic(
        country=test_data["countries"][0],
         rng=random.Random(7),
    )
    assert isinstance(demo_data, DemographicData)
    assert demo_data.region in Region.all_instances()
    assert demo_data.country in demo_data.region.countries
    assert demo_data.subtype in demo_data.country.eth_mix
    assert demo_data.gender in [Gender.XX, Gender.XY]


def test_demographic_sampling_with_params(test_data):
    region = test_data["regions"][0]  # Europe
    country = test_data["countries"][0]  # France
    subtype = test_data["subtypes"][0]  # French
    gender = Gender.XX

    demo_data = DemographicSampler.sample_demographic(
        region=region, country=country, subtype=subtype, gender=gender,

         rng=random.Random(7),
    )

    assert demo_data.region == region
    assert demo_data.country == country
    assert demo_data.gender == gender


def test_demographic_sampling_normalizes_string_inputs(test_data):
    demo_data = DemographicSampler.sample_demographic(
        country="fra",
        subtype="european",
        gender="XX",
        age_range="ADULT",

         rng=random.Random(7),
    )

    assert isinstance(demo_data.region, Region)
    assert demo_data.region.label == "west_europe"
    assert isinstance(demo_data.country, Country)
    assert demo_data.country.label == "fra"
    assert isinstance(demo_data.subtype, Subtype)
    assert demo_data.subtype.label == "european"
    assert isinstance(demo_data.gender, Gender)
    assert demo_data.gender is Gender.XX
    assert isinstance(demo_data.age_range, AgeRange)
    assert demo_data.age_range is AgeRange.ADULT


def test_demonym_property():
    demo_data = DemographicData(
        region=Region(label="demonym_region", name="Test Region", demonym="Test Regional", eth_mix={}),
        country=Country(label="demonym_country", name="Test Country", demonym="Test National", population=1000000),
        subtype=Subtype(label="demonym_subtype", name="Test Subtype", demonym="Test Subtype")
    )

    assert demo_data.demonym == "Test Regional"

    demo_data.region = None
    assert demo_data.demonym == "Test National"

    demo_data.country = None
    logging.debug(demo_data.subtype)
    assert demo_data.demonym == "Test Subtype"

def test_full_demographic_sampling(test_data):
    demo = DemographicSampler.sample_demographic(
        country=test_data["countries"][0],
         rng=random.Random(7),
    )
    assert isinstance(demo, DemographicData)
    assert demo.region is not None
    assert demo.country is not None
    assert demo.subtype is not None
    assert demo.gender is not None
    assert demo.age_range is not None


def test_demographic_sampling_with_explicit_rng_is_reproducible(test_data):
    left = DemographicSampler.sample_demographic(
        country="fra",
         rng=random.Random(7),
    )
    right = DemographicSampler.sample_demographic(
        country="fra",
         rng=random.Random(7),
    )

    assert left.region.label == right.region.label
    assert left.country.label == right.country.label
    assert left.subtype.label == right.subtype.label
    assert left.gender == right.gender
    assert left.age_range == right.age_range
