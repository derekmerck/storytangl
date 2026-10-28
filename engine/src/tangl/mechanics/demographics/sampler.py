from __future__ import annotations

from collections.abc import Sequence
import logging
import random
from typing import Any

from tangl.core import TokenCatalog
from tangl.lang.age_range import AgeRange
from tangl.lang.gens import Gens as Gender
from tangl.lang.personal_name import PersonalName

from .data_models import Subtype, Country, Region, NameBank, NamePart, NamePool
from .demographic import DemographicData
from .selection import select_bank

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def _sample_pool(pool: NamePool, rng: random.Random) -> str:
    if pool.weights is None:
        return rng.choice(pool.candidates)
    eligible = [
        (value, weight)
        for value, weight in zip(pool.candidates, pool.weights, strict=True)
        if weight > 0
    ]
    scale = max(weight for _value, weight in eligible)
    return rng.choices(
        [value for value, _weight in eligible],
        weights=[weight / scale for _value, weight in eligible], k=1,
    )[0]


def _sample_part(part: NamePart, rng: random.Random) -> str:
    stem = _sample_pool(part.pool, rng)
    stem = part.substitutions.get(stem, stem)
    if part.prefix is not None:
        stem = _sample_pool(part.prefix, rng) + part.prefix_separator + stem
    if part.suffix is not None:
        stem += part.suffix_separator + _sample_pool(part.suffix, rng)
    return stem


class DemographicSampler:
    """
    Samples region, country, subtype, gender, and name

    Geography/profile helpers sample omitted facts under the existing policy.
    Naming requires an explicit form, catalog scope, and RNG; forms are not
    inferred from gender or geography.

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

        countries = sorted(
            region.countries,
            key=lambda country: getattr(country, "label", "") or getattr(country, "name", ""),
        )

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
        gender = Gender.pick(rand=cls._rand(rng))
        return gender

    @classmethod
    def sample_age_range(cls, weighted: bool = False, rng: Any = None) -> AgeRange:
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
    def _normalize_age_range(
        cls,
        age_range: AgeRange = None,
        weighted: bool = True,
        rng: Any = None,
    ) -> AgeRange:
        if age_range is None:
            age_range = cls.sample_age_range(weighted=weighted, rng=rng)
        elif not isinstance(age_range, AgeRange):
            age_range = AgeRange(age_range)
        return age_range

    @classmethod
    def sample_name(
        cls,
        nb: NameBank | str,
        *,
        form: str,
        catalogs: Sequence[TokenCatalog[NameBank]],
        rng: random.Random,
        gender: Gender = Gender.X_,
    ) -> PersonalName:
        """Form a scoped name without inferring pools from gender or geography."""
        bank = select_bank(nb, catalogs=catalogs, rng=rng)
        if form not in bank.forms:
            raise LookupError(f"NameBank {bank.label!r} has no form {form!r}")
        declaration = bank.forms[form]
        parts: dict[str, str] = {}
        if declaration.given is not None:
            parts["given_name"] = _sample_part(declaration.given, rng)
        if declaration.family is not None:
            parts["family_name"] = _sample_part(declaration.family, rng)
        return PersonalName(**parts, title="", gender=gender)

    @classmethod
    def sample_demographic(
        cls,
        region: Region = None,
        country: Country = None,
        subtype: Subtype = None,
        gender: Gender = None,
        age_range: AgeRange = None,
        weighted: bool = True,
        *,
        catalogs: Sequence[TokenCatalog[NameBank]],
        rng: random.Random,
        fallback_bank: str | None = None,
        name_form: str,
    ) -> DemographicData:

        country = (
            cls._normalize_country(country, region=region, weighted=weighted, rng=rng)
            if country is not None
            else None
        )

        if region is None and country is not None:
            region = country.region
        region = cls._normalize_region(region, weighted=weighted, rng=rng)
        country = cls._normalize_country(country, region=region, weighted=weighted, rng=rng)
        subtype = cls._normalize_subtype(
            subtype,
            country=country,
            region=region,
            weighted=weighted,
            rng=rng,
        )
        gender = cls._normalize_gender(gender, weighted=weighted, rng=rng)
        age_range = cls._normalize_age_range(age_range, weighted=weighted, rng=rng)

        nb = country.namebank(subtype, catalogs=catalogs, fallback_bank=fallback_bank)
        name = cls.sample_name(
            nb, form=name_form, gender=gender, catalogs=catalogs, rng=rng,
        )

        return DemographicData(
            given_name=name.given_name,
            family_name=name.family_name,
            region=region,
            country=country,
            subtype=subtype,
            gender=gender,
            age_range=age_range)
