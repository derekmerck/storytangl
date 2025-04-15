import itertools

import pytest

from tangl.mechanics.demographics import DemographicSampler, DemographicData
from tangl.mechanics.demographics.data_models import Region, Country, Subtype
from tangl.mechanics.demographics.data_models import load_demographic_distributions, Region, Country, Subtype

@pytest.fixture(autouse=True, scope='module')
def load_default_data():
    Region.clear_instances()
    Country.clear_instances()
    Subtype.clear_instances()
    load_demographic_distributions()


def test_demographic_data():

    for r in Region._instances.values():
        print( r.name )

    for c in Country._instances.values():
        print( c.name )


def test_demographic_sampler():

    print( DemographicSampler.sample_region().name )
    print( DemographicSampler.sample_country().name )
    print( DemographicSampler.sample_country( region=Region.get_instance('asia') ) )
    print( DemographicSampler.sample_subtype() )
    print( DemographicSampler.sample_subtype( country=Country.get_instance('jpn') ) )
    print( DemographicSampler.sample_subtype( region=Region.get_instance('west_europe') ) )


def test_name_sampler():

    print( DemographicSampler.sample_xx_name('fra' ) )
    print( DemographicSampler.sample_xy_name('jpn' ) )


# @pytest.mark.parametrize("country,subtype", itertools.product( Country._instances.keys(), Subtype._instances.keys() ))
# todo: need to fix subtype handler
@pytest.mark.xfail(raises=KeyError)
@pytest.mark.parametrize("country", Country._instances.values())
def test_name_sampler_variations(country: str):

    female_name = DemographicSampler.sample_xx_name(country.label)
    male_name = DemographicSampler.sample_xy_name(country.label)
    print( country.name, female_name, male_name )

# def test_demographic_factory():
#
#     d = DemographicFactory.create_demographic()
#
#     print( d )
#
# def test_faker():
#
#     fake = Faker()
#     fake.add_provider( DemographicProvider )
#
#     d = fake.demographic(country="cog")
#     print( d )

def test_country_data_singleton():
    # Test that CountryData instances are unique and correctly instantiated
    angola = Country.get_instance('ago')
    assert angola.label == 'ago'
    assert angola.population == 31825295
    assert angola.demonym == 'Angolan'

def test_region_data_population():
    # Test the population attribute in RegionData
    africa = Region.get_instance('africa')
    assert africa.population == 1109541977

# def test_name_sampler_consistency():
#     from tangl.mechanics.demographics.demographic_data import world_name_data
#     # Test if NameSampler returns correct names based on country and subtype
#     angolan_names = NameSampler.name_female(CountryData['ago'], 'black')
#     assert angolan_names[0] in world_name_data['ago']['female']
#
# def test_demographic_sampler2():
#     # Test DemographicSampler for correct region and country sampling
#     sampled_country = DemographicSampler.sample_country()
#     assert sampled_country in CountryData
#
# def test_ethnicity_mix_sampling():
#     # Test if the sampled subtype is from the country's ethnic mix
#     subtype = DemographicSampler.sample_subtype(CountryData['ago'])
#     assert subtype.value in CountryData['ago'].eth_mix
#


