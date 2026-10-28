from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Self

from pydantic import ConfigDict, Field, model_validator

from tangl.core import Singleton, TokenCatalog
from tangl.core.bases import Unstructurable


class Subtype(Singleton):
    """Historical population category used by the optional geography data."""

    name: str | None = None
    demonym: str | None = None


class NamePool(Unstructurable):
    """Ordered candidates, retaining duplicate multiplicity and optional weights."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidates: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    weights: list[Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)]] | None = None

    @model_validator(mode="after")
    def validate_weights(self) -> Self:
        if self.weights is not None:
            if len(self.weights) != len(self.candidates):
                raise ValueError("Name pool weights must match candidate positions")
            if not any(weight > 0 for weight in self.weights):
                raise ValueError("Name pool requires positive eligible weight")
        return self


class NamePart(Unstructurable):
    """Select a stem, apply exact substitutions, then attach literal affixes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pool: NamePool = Field(json_schema_extra={"unstructurable": True})
    prefix: NamePool | None = Field(default=None, json_schema_extra={"unstructurable": True})
    suffix: NamePool | None = Field(default=None, json_schema_extra={"unstructurable": True})
    prefix_separator: str = ""
    suffix_separator: str = ""
    substitutions: dict[str, Annotated[str, Field(min_length=1)]] = Field(
        default_factory=dict, json_schema_extra={"include": True},
    )


class NameForm(Unstructurable):
    """Declared given/family parts; either may be explicitly absent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    given: NamePart | None = Field(default=None, json_schema_extra={"unstructurable": True})
    family: NamePart | None = Field(default=None, json_schema_extra={"unstructurable": True})

    @model_validator(mode="after")
    def require_part(self) -> Self:
        if self.given is None and self.family is None:
            raise ValueError("A name form requires a given or family part")
        return self


class NameBank(Singleton):
    """Shared naming forms; callers choose arbitrary form keys explicitly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    selection_key: str | None = Field(
        default=None, min_length=1, json_schema_extra={"is_identifier": True},
    )
    forms: dict[str, NameForm] = Field(
        min_length=1, json_schema_extra={"unstructurable": True, "include": True},
    )


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
