"""
Test real demographic DATA QUALITY and coverage.

These tests verify that the actual LFS-backed demographic data has the expected
structure, populations, and name coverage.

Tests skip gracefully when LFS data is unavailable.
"""

import pytest

from tangl.mechanics.demographics import DemographicSampler
from tangl.mechanics.demographics.data_models import (
    Country,
    NameBank,
    Region,
    Subtype,
    load_demographic_distributions,
)

def _has_real_demographic_data() -> bool:
    """Check if real demographic data was successfully loaded."""
    country_count = sum(1 for _ in Country.all_instances())
    namebank_count = sum(1 for _ in NameBank.all_instances())
    return country_count > 5 and namebank_count > 5


# All tests in this module require real data
pytestmark = pytest.mark.skipif(
    not _has_real_demographic_data(),
    reason="Real demographic data not available (LFS not pulled or data failed to load)",
)


@pytest.fixture(autouse=True, scope="module")
def load_real_data():
    """Load real demographic distributions for testing."""
    Region.clear_instances()
    Country.clear_instances()
    Subtype.clear_instances()
    NameBank.clear_instances()
    load_demographic_distributions()


def test_demographic_data_loaded():
    """Verify that real demographic data is present."""
    regions = list(Region.all_instances())
    countries = list(Country.all_instances())

    assert len(regions) > 5, "Should have multiple regions"
    assert len(countries) > 50, "Should have many countries"

    for region in regions:
        print(region.name)

    for country in countries:
        print(country.name)


def test_major_regions_present():
    """Test that expected major regions exist."""
    region_labels = {r.label for r in Region.all_instances()}
    expected = {"africa", "asia", "europe"}
    assert expected.issubset(region_labels), f"Missing regions: {expected - region_labels}"


def test_demographic_sampler():
    """Test that sampler works with real data."""
    print(DemographicSampler.sample_region().name)
    print(DemographicSampler.sample_country().name)
    print(DemographicSampler.sample_country(region=Region.get_instance("asia")))
    print(DemographicSampler.sample_subtype())
    print(DemographicSampler.sample_subtype(country=Country.get_instance("jpn")))


def test_name_sampler():
    """Test that name sampling works with real data."""
    print(DemographicSampler.sample_xx_name("fra"))
    print(DemographicSampler.sample_xy_name("jpn"))


def country_params():
    """Generate test parameters for all countries."""
    for country in Country.all_instances():
        marks = []
        if country.label in ["zaf", "usa"]:
            marks.append(
                pytest.mark.xfail(
                    reason="zaf and usa require subtype specification",
                )
            )
        yield pytest.param(country, marks=marks, id=country.label)


@pytest.mark.parametrize("country", country_params())
def test_name_sampler_variations(country: Country):
    """Test that every country can generate valid names."""
    female_name = DemographicSampler.sample_xx_name(country.label)
    male_name = DemographicSampler.sample_xy_name(country.label)
    print(country.name, female_name, male_name)


def test_country_data_singleton():
    """Test specific country data accuracy."""
    angola = Country.get_instance("ago")
    assert angola.label == "ago"
    assert angola.population == 31_825_295
    assert angola.demonym == "Angolan"


def test_region_data_population():
    """Test region population calculations."""
    africa = Region.get_instance("africa")
    assert africa.population == 1_109_541_977
