from __future__ import annotations

from pydantic import Field

from tangl.core.singleton import Singleton


class Subtype(Singleton):
    """Historical population category used by the optional geography data."""

    name: str | None = None
    demonym: str | None = None


class NameBank(Singleton):
    """Shared name pools; loading and registration are explicit pack operations."""

    xx_names: list[str] = Field(alias="female")
    xy_names: list[str] | None = Field(None, alias="male")
    surname: list[str]
    xy_surname: dict[str, str] | None = Field(None, alias="male_surnames")


class Country(Singleton):
    """Historical geography and optional country-specific population mixture."""

    name: str
    demonym: str
    population: int
    eth_mix_: dict[Subtype, int] | None = Field(None, alias="eth_mix")

    @property
    def region(self) -> Region | None:
        for region in Region.all_instances():
            if self in region.countries:
                return region
        return None

    @property
    def eth_mix(self) -> dict[Subtype, int]:
        return self.eth_mix_ or self.region.eth_mix

    def namebank(self, subtype: Subtype | str | None = None) -> NameBank | None:
        if subtype:
            if isinstance(subtype, Subtype):
                subtype = subtype.label
            key = f"{self.label}_{subtype}"
            if bank := NameBank.get_instance(key):
                return bank
        return NameBank.get_instance(self.label)


class Region(Singleton):
    """A shared collection of countries and its historical population mixture."""

    label_: str = Field(alias="label")
    name: str
    demonym: str
    eth_mix: dict[Subtype, int]
    countries: set[Country] = Field(default_factory=set)

    @property
    def population(self) -> int:
        return sum(country.population for country in self.countries)
