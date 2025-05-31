import random
import logging

from tangl.narrative.lang.gens import Gens as Gender
from tangl.narrative.lang.age_range import AgeRange
from .data_models import Subtype, Country, Region, NameBank
from .demographic import DemographicData

logger = logging.getLogger(__name__)

class DemographicSampler:
    """
    Samples region, country, subtype, gender, and name

    If arguments are omitted, a random substitute is generated and propagated
    through the selection process.

    methods:
    - `sample_demographic(region, country, subtype, gender) -> DemographicData`
    - `sample_gender() -> Gender`
    - `sample_subtype(country) -> Subtype`
    - `sample_country(region) -> Country`
    - `sample_region() -> Region`
    """

    @classmethod
    def sample_region(cls, weighted=False) -> Country:
        regions = list(Region._instances.values())  # type: list[Region]
        if not regions:
            raise IndexError('No regions found')
        if weighted:
            # Population weighted dist
            return random.choices(regions, weights=[r.population for r in regions], k=1)[0]
        else:
            # Uniform dist
            return random.choice(regions)

    @classmethod
    def _normalize_region(cls, region: Region = None, weighted=True) -> Region:
        if region is None:
            region = cls.sample_region(weighted=weighted)
        elif not isinstance(region, Region):
            region = Region.get_instance(region)
        return region

    @classmethod
    def sample_country(cls, region: Region = None, weighted=True) -> Country:
        region = cls._normalize_region(region, weighted=weighted)

        countries = list(region.countries)  # it's a set, so order it

        if not countries:
            raise IndexError('No countries found')

        if weighted:
            # Population weighted dist
            logger.debug(countries)
            return random.choices(countries, weights=[c.population for c in countries], k=1)[0]
        else:
            # Uniform dist
            return random.choice(countries)

    @classmethod
    def _normalize_country(cls, country: Country, region: Region = None, weighted=True) -> Country:
        if not country:
            country = cls.sample_country(region=region, weighted=weighted)
        elif isinstance(country, str):
            country = Country.get_instance(country)
        return country

    @classmethod
    def sample_subtype(cls, country: Country = None, region: Region = None, weighted=False) -> Subtype:
        if region:
            region = cls._normalize_region(region, weighted=weighted)
            eth_mix = region.eth_mix
        else:
            country = cls._normalize_country(country, weighted=weighted)
            eth_mix = country.eth_mix
        subtype = random.choices(
            [*eth_mix.keys()],
            weights=[*eth_mix.values()], k=1)[0]
        return subtype

    @classmethod
    def _normalize_subtype(cls, subtype: Subtype,
                           country: Country,
                           region: Region,
                           weighted=True) -> Subtype:
        country = cls._normalize_country(country, region=region, weighted=weighted)
        # note, a _new_ country or region may be picked here.  Regions are findable via
        # country, but countries are _not_ findable via subtype name
        if not subtype:
            subtype = cls.sample_subtype(country=country, weighted=weighted)
        elif isinstance(subtype, str):
            subtype = Subtype.get_instance(subtype)
        return subtype

    @classmethod
    def sample_gender(cls, weighted=False) -> Gender:
        # todo: could apply artificial gender weighting here
        gender = Gender.pick()
        return gender

    @classmethod
    def sample_age_range(cls, weighted=False) -> Gender:
        # todo: could definitely find age distributions per region at least
        age_range = random.choice([*AgeRange.__members__.values()])
        return age_range

    @classmethod
    def _normalize_gender(cls, gender: Gender = None, weighted=True) -> Gender:
        if not gender:
            gender = cls.sample_gender(weighted=weighted)
        elif not isinstance(gender, Gender):
            gender = Gender(gender)
        return gender

    @classmethod
    def _normalize_nb(cls, namebank: NameBank | str) -> NameBank:
        if namebank is None:
            raise KeyError(f'No NameBank provided')
        if isinstance(namebank, str):
            passed_str = namebank
            namebank = NameBank.get_instance(namebank)
            if namebank is None:
                raise KeyError(f'No NameBank found for {passed_str}')
        return namebank

    @classmethod
    def sample_xx_name(cls, nb: NameBank) -> tuple[str, str]:
        nb = cls._normalize_nb(nb)
        given_name = random.choice(nb.xx_names)
        family_name = random.choice(nb.surname)
        return given_name, family_name

    @classmethod
    def sample_xy_name(cls, nb: NameBank) -> tuple[str, str]:
        nb = cls._normalize_nb(nb)
        if nb.xy_names:
            # Not guaranteed to have male names
            given_name = random.choice(nb.xy_names)
        else:
            given_name = random.choice(nb.xx_names)
        family_name = random.choice(nb.surname)
        if nb.xy_surname:
            family_name = nb.xy_surname.get(family_name, family_name)
        return given_name, family_name

    @classmethod
    def sample_namebank(cls, nb: NameBank, gender: Gender = None) -> tuple[str, str]:
        nb = cls._normalize_nb(nb)
        # No name popularity stats, assume gender is 50/50, so no weighted sampling
        gender = cls._normalize_gender(gender)

        if gender is Gender.XY:
            return cls.sample_xy_name(nb)

        return cls.sample_xx_name(nb)

    @classmethod
    def sample_demographic(cls, region: Region = None, country: Country = None, subtype: Subtype = None, gender: Gender = None, age_range: AgeRange = None, weighted=True) -> DemographicData:

        region = region or cls.sample_region()
        country = country or cls.sample_country(region=region)
        subtype = subtype or cls.sample_subtype(country=country)
        gender = gender or cls.sample_gender()
        age_range = age_range or cls.sample_age_range()

        nb = country.namebank(subtype)
        given_name, family_name = cls.sample_namebank(nb, gender=gender)

        return DemographicData(
            given_name=given_name,
            family_name=family_name,
            region=region,
            country=country,
            subtype=subtype,
            gender=gender,
            age_range=age_range)

