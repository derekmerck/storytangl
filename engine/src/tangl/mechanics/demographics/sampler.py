import random
import logging
from typing import Any

from tangl.lang.gens import Gens as Gender
from tangl.lang.age_range import AgeRange
from .data_models import Subtype, Country, Region, NameBank
from .demographic import DemographicData

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

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

    @staticmethod
    def _rand(rng: Any = None) -> Any:
        return rng or random

    @classmethod
    def sample_region(cls, weighted: bool = False, rng: Any = None) -> Region:
        regions = list(Region.all_instances())  # type: list[Region]
        if not regions:
            raise IndexError('No regions found')
        rand = cls._rand(rng)
        if weighted:
            # Population weighted dist
            return rand.choices(regions, weights=[r.population for r in regions], k=1)[0]
        else:
            # Uniform dist
            return rand.choice(regions)

    @classmethod
    def _normalize_region(cls, region: Region = None, weighted: bool = True, rng: Any = None) -> Region:
        if region is None:
            region = cls.sample_region(weighted=weighted, rng=rng)
        elif not isinstance(region, Region):
            region = Region.get_instance(region)
        return region

    @classmethod
    def sample_country(cls, region: Region = None, weighted: bool = True, rng: Any = None) -> Country:
        region = cls._normalize_region(region, weighted=weighted, rng=rng)

        countries = list(region.countries)  # it's a set, so order it

        if not countries:
            raise IndexError('No countries found')

        rand = cls._rand(rng)
        if weighted:
            # Population weighted dist
            logger.debug(countries)
            return rand.choices(countries, weights=[c.population for c in countries], k=1)[0]
        else:
            # Uniform dist
            return rand.choice(countries)

    @classmethod
    def _normalize_country(
        cls,
        country: Country,
        region: Region = None,
        weighted: bool = True,
        rng: Any = None,
    ) -> Country:
        if not country:
            country = cls.sample_country(region=region, weighted=weighted, rng=rng)
        elif isinstance(country, str):
            country = Country.get_instance(country)
        return country

    @classmethod
    def sample_subtype(
        cls,
        country: Country = None,
        region: Region = None,
        weighted: bool = False,
        rng: Any = None,
    ) -> Subtype:
        if region:
            region = cls._normalize_region(region, weighted=weighted, rng=rng)
            eth_mix = region.eth_mix
        else:
            country = cls._normalize_country(country, weighted=weighted, rng=rng)
            eth_mix = country.eth_mix
        rand = cls._rand(rng)
        subtype = rand.choices(
            [*eth_mix.keys()],
            weights=[*eth_mix.values()], k=1)[0]
        return subtype

    @classmethod
    def _normalize_subtype(
        cls,
        subtype: Subtype,
        country: Country,
        region: Region,
        weighted: bool = True,
        rng: Any = None,
    ) -> Subtype:
        country = cls._normalize_country(country, region=region, weighted=weighted, rng=rng)
        # note, a _new_ country or region may be picked here.  Regions are findable via
        # country, but countries are _not_ findable via subtype name
        if not subtype:
            subtype = cls.sample_subtype(country=country, weighted=weighted, rng=rng)
        elif isinstance(subtype, str):
            subtype = Subtype.get_instance(subtype)
        return subtype

    @classmethod
    def sample_gender(cls, weighted: bool = False, rng: Any = None) -> Gender:
        # todo: could apply artificial gender weighting here
        gender = Gender.pick(rand=cls._rand(rng))
        return gender

    @classmethod
    def sample_age_range(cls, weighted: bool = False, rng: Any = None) -> AgeRange:
        # todo: could definitely find age distributions per region at least
        age_range = cls._rand(rng).choice([*AgeRange.__members__.values()])
        return age_range

    @classmethod
    def _normalize_gender(cls, gender: Gender = None, weighted: bool = True, rng: Any = None) -> Gender:
        if not gender:
            gender = cls.sample_gender(weighted=weighted, rng=rng)
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
    def sample_xx_name(cls, nb: NameBank, rng: Any = None) -> tuple[str, str]:
        nb = cls._normalize_nb(nb)
        rand = cls._rand(rng)
        given_name = rand.choice(nb.xx_names)
        family_name = rand.choice(nb.surname)
        return given_name, family_name

    @classmethod
    def sample_xy_name(cls, nb: NameBank, rng: Any = None) -> tuple[str, str]:
        nb = cls._normalize_nb(nb)
        rand = cls._rand(rng)
        if nb.xy_names:
            # Not guaranteed to have male names
            given_name = rand.choice(nb.xy_names)
        else:
            given_name = rand.choice(nb.xx_names)
        family_name = rand.choice(nb.surname)
        if nb.xy_surname:
            family_name = nb.xy_surname.get(family_name, family_name)
        return given_name, family_name

    @classmethod
    def sample_namebank(cls, nb: NameBank, gender: Gender = None, rng: Any = None) -> tuple[str, str]:
        nb = cls._normalize_nb(nb)
        # No name popularity stats, assume gender is 50/50, so no weighted sampling
        gender = cls._normalize_gender(gender, rng=rng)

        if gender is Gender.XY:
            return cls.sample_xy_name(nb, rng=rng)

        return cls.sample_xx_name(nb, rng=rng)

    @classmethod
    def sample_demographic(
        cls,
        region: Region = None,
        country: Country = None,
        subtype: Subtype = None,
        gender: Gender = None,
        age_range: AgeRange = None,
        weighted: bool = True,
        rng: Any = None,
    ) -> DemographicData:

        region = region or cls.sample_region(weighted=weighted, rng=rng)
        country = country or cls.sample_country(region=region, weighted=weighted, rng=rng)
        subtype = subtype or cls.sample_subtype(country=country, weighted=weighted, rng=rng)
        gender = gender or cls.sample_gender(weighted=weighted, rng=rng)
        age_range = age_range or cls.sample_age_range(weighted=weighted, rng=rng)

        nb = country.namebank(subtype)
        given_name, family_name = cls.sample_namebank(nb, gender=gender, rng=rng)

        return DemographicData(
            given_name=given_name,
            family_name=family_name,
            region=region,
            country=country,
            subtype=subtype,
            gender=gender,
            age_range=age_range)
