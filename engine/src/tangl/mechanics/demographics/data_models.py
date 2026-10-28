from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from tangl.core import Singleton, TokenCatalog


class Subtype(Singleton):
    """Historical population category used by the optional geography data."""

    name: str | None = None
    demonym: str | None = None


class NameBank(Singleton):
    """Shared name pools; loading and registration are explicit pack operations."""

    selection_key: str | None = Field(
        default=None, min_length=1, json_schema_extra={"is_identifier": True},
    )

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

    def namebank(
        self,
        subtype: Subtype | str | None = None,
        *,
        catalogs: Sequence[TokenCatalog[NameBank]],
        fallback_bank: str | None = None,
    ) -> NameBank:
        """Resolve the exact country/subtype bank or an explicitly declared fallback."""
        from .selection import select_bank

        key = self.label
        if subtype:
            key = f"{self.label}_{subtype.label if isinstance(subtype, Subtype) else subtype}"
        try:
            return select_bank(key, catalogs=catalogs)
        except LookupError:
            if fallback_bank is None:
                raise
            return select_bank(fallback_bank, catalogs=catalogs)


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
