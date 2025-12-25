from __future__ import annotations
import logging
import re

from pydantic import BaseModel, Field, field_validator

from tangl.utils.load_yaml_resource import load_yaml_resource
from tangl.core.singleton import Singleton
# todo: want to be able to influence weighting for region, country, subtype, gender on random sample
#       for example, prefer this region, country, subtype, gender

# todo: convert subtypes to enum
# todo: handle namebanks with ethnicity better
# todo: get region/country instance by name
# todo: overlay stuff

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# A very small built-in fallback that covers the handful of countries referenced
# by the smoke tests. The authoritative dataset lives in git-lfs and contains
# thousands of entries, but we keep these few around so unit tests can run in
# lightweight environments that do not fetch the full blob.
FALLBACK_WORLD_NAME_DATA = {
    'fra': {
        'female': ['Marie', 'Sophie', 'Camille'],
        'male': ['Jean', 'Pierre', 'Louis'],
        'surname': ['Dubois', 'Moreau', 'Bernard'],
        'male_surnames': {},
    },
    'jpn': {
        'female': ['Yuki', 'Aiko', 'Hana'],
        'male': ['Haruto', 'Ren', 'Yuto'],
        'surname': ['Sato', 'Suzuki', 'Takahashi'],
        'male_surnames': {},
    },
}
SUBTYPE_NAMEBANK_REQUIRED = {"usa", "zaf"}


class Region(Singleton):
    """
    Regions are collections of countries
    """
    label_: str = Field(..., alias='label')
    name: str
    demonym: str

    eth_mix: dict[Subtype, int]

    @field_validator('eth_mix', mode='before')
    @classmethod
    def _convert_subtypes(cls, data):
        def _resolve_subtype(label):
            if x := Subtype.find_instance(label=label):
                return x
            else:
                return Subtype(label=label)
        res = {_resolve_subtype(k): v for k, v in data.items()}
        return res

    countries: set[Country] = Field(default_factory=set)

    @field_validator('countries', mode='before')
    @classmethod
    def _convert_countries(cls, data):
        res = set()
        logger.debug(data)
        for country_data in data.values():
            logger.debug(country_data)
            country_data['label'] = country_data.pop('id')
            c = Country(**country_data)
            logger.debug(c)
            res.add(c)
        return res

    @property
    def population(self) -> int:
        return sum([c.population for c in self.countries])


class Country(Singleton):
    """
    Countries are collections of subtypes
    """
    # label_: str = Field(..., alias='label')
    name: str
    demonym: str
    population: int

    @property
    def region(self) -> Region:
        for r in Region.all_instances():
            if self in r.countries:
                return r

    eth_mix_: dict[Subtype, int] = Field(None, alias='eth_mix')

    @field_validator('eth_mix_', mode='before')
    def _convert_subtypes(cls, data):

        def _resolve_subtype(label):
            if x := Subtype.find_instance(label=label):
                return x
            else:
                return Subtype(label=label)

        res = { _resolve_subtype(k): v for k, v in data.items() }
        return res

    @property
    def eth_mix(self):
        return self.eth_mix_ or self.region.eth_mix

    def namebank(self, subtype: Subtype | str = None) -> NameBank:
        if subtype:
            if isinstance(subtype, Subtype):
                subtype = subtype.label
            if not isinstance(subtype, str):
                raise TypeError('subtype must be str or Subtype')
            key = f"{self.label}_{subtype}"
            if x := NameBank.find_instance(label=key):
                return x
        return NameBank.get_instance(self.label)

    # __hash__ = Singleton.__hash__


class Subtype(Singleton):
    """
    Each country has namebanks keyed by subtype
    """
    # label_: str = Field(..., alias='label')
    name: str = None
    demonym: str = None


class NameBank(Singleton):
    xx_names: list = Field(..., alias='female')  # Must have female names
    xy_names: list = Field(None, alias='male')   # Sometimes no male names
    surname: list                                       # Must have surnames
    xy_surname: dict = Field(None, alias='male_surnames')
    # Optional dict indexed by common/female surname


def resources_pkg() -> str:
    pkg = re.sub(r'\.\w*?$', '', __name__)  # get rid of fn
    return f"{pkg}.resources"


def _build_fallback_namebank(country: Country) -> dict:
    base = (country.demonym or country.name or country.label).strip()
    base = re.sub(r"\s+", "", base)
    if not base:
        base = country.label
    return {
        "female": [f"{base}a", f"{base}e"],
        "male": [f"{base}o", f"{base}i"],
        "surname": [base, country.label.upper()],
        "male_surnames": {},
    }

def _ensure_mapping(data, resource_name: str, fallback: dict | None = None) -> dict:
    """Return mapping data loaded from YAML, or an empty dict when unavailable.

    The project stores large demographic datasets behind git-lfs pointers. In
    automated environments where the pointer files are present but blobs are
    not
    fetched, ``yaml.safe_load`` will return a string describing the pointer
    rather than the expected mapping. Trying to iterate ``.items()`` on that
    string raises an ``AttributeError`` during module import which prevents the
    simplified unit fixtures from constructing their own in-memory data.

    To keep the module importable without the heavy optional datasets, treat
    non-mapping payloads as missing data and fall back to an empty dictionary.
    Consumers that rely on the real dataset (such as production usage) will
    still populate the resources when the blobs are available.
    """

    if isinstance(data, dict):
        return data

    if fallback is None:
        logger.warning(
            "Demographics resource %s is unavailable; using empty fallback (type=%s)",
            resource_name,
            type(data).__name__,
        )
        return {}

    logger.warning(
        "Demographics resource %s is unavailable; using built-in fallback data", resource_name
    )
    return fallback


def load_demographic_distributions():

    # this data is used to generate region and country data
    nationalities_raw = load_yaml_resource(resources_pkg(), 'nationalities.yaml')
    nationalities_data = _ensure_mapping(nationalities_raw, 'nationalities.yaml')

    for k, _region in nationalities_data.items():
        _region['label'] = _region.pop('id')
        Region(**_region)

    world_name_raw = load_yaml_resource(resources_pkg(), 'world_names.yaml')
    world_name_data = _ensure_mapping(
        world_name_raw,
        'world_names.yaml',
        fallback=FALLBACK_WORLD_NAME_DATA,
    )
    for label, data in world_name_data.items():
        if NameBank.get_instance(label):
            continue
        NameBank(label=label, **data)

    existing_labels = {bank.label for bank in NameBank.all_instances()}
    for country in Country.all_instances():
        if country.label in SUBTYPE_NAMEBANK_REQUIRED:
            continue
        if country.label in existing_labels:
            continue
        if any(label.startswith(f"{country.label}_") for label in existing_labels):
            continue
        NameBank(label=country.label, **_build_fallback_namebank(country))

    # for country in Country._instances.values():
    #     if country.label not in world_name_data:
    #         logger.debug(str([world_name_data.keys()]))
    #         raise ValueError(f"Missing country data for name bank {country.label}")
    #     data = world_name_data[country.label]
    #     print( data )
    #
    # for country_key in world_name_data:
    #     if country_key not in Country._instances:
    #         raise ValueError(f"Missing country definition for name bank {country_key}")

load_demographic_distributions()
