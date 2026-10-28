"""Explicit loading of the illustrative sample and optional historical full pack.

Parsing validates resource data without registering Singletons. Registration reuses
identical definitions and rejects conflicting labels; it never clears a registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
import yaml

from .data_models import Country, NameBank, Region, Subtype


class PackUnavailableError(FileNotFoundError):
    """A requested resource is absent or still a Git LFS pointer."""


class _CountryData(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    name: str
    demonym: str
    population: int
    eth_mix: dict[str, int] | None = None


class _RegionData(_CountryData):
    countries: dict[str, _CountryData]
    eth_mix: dict[str, int]


class _NameData(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    female: list[str] = Field(min_length=1)
    male: list[str] | None = None
    surname: list[str] = Field(min_length=1)
    male_surnames: dict[str, str] | None = None


class PackMetadata(BaseModel):
    """Source claims and known limits of a shipped pack, not an availability claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: Literal["sample", "full"]
    revision: str
    source: str
    geography: str
    transformations: str
    provenance_gaps: list[str]


@dataclass
class DemographicPack:
    """Validated resource data; constructing this value does not register anything."""

    metadata: PackMetadata
    regions: dict[str, _RegionData]
    names: dict[str, _NameData]

    def uncovered_subtypes(self) -> tuple[tuple[str, str], ...]:
        """Report missing exact subtype banks, without applying fallback policy."""
        return tuple(
            (country.id, subtype)
            for region in self.regions.values()
            for country in region.countries.values()
            for subtype in sorted(country.eth_mix or region.eth_mix)
            if f"{country.id}_{subtype}" not in self.names
        )

    def countries_without_banks(self) -> tuple[str, ...]:
        """Countries with neither a base bank nor any subtype bank in this pack."""
        return tuple(
            country.id
            for region in self.regions.values()
            for country in region.countries.values()
            if country.id not in self.names
            and not any(label.startswith(f"{country.id}_") for label in self.names)
        )


def parse_pack(
    metadata: PackMetadata,
    geography: object,
    names: object,
) -> DemographicPack:
    """Validate and copy parsed YAML mappings without registration or input mutation."""
    regions = TypeAdapter(dict[str, _RegionData]).validate_python(geography)
    banks = TypeAdapter(dict[str, _NameData]).validate_python(names)
    country_ids: set[str] = set()
    for key, region in regions.items():
        if key != region.id:
            raise ValueError(f"Region key {key!r} differs from id {region.id!r}")
        for label, country in region.countries.items():
            if label != country.id or label in country_ids:
                raise ValueError(f"Conflicting country id: {label!r}")
            country_ids.add(label)
    if not regions or not banks:
        raise ValueError("A demographics pack requires geography and name banks")
    return DemographicPack(metadata, regions, banks)


def _read_yaml(filename: str) -> object:
    resource = files(__package__).joinpath("resources", filename)
    try:
        text = resource.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PackUnavailableError(f"Demographics resource {filename!r} is absent") from exc
    if text.startswith("version https://git-lfs.github.com/spec/v1\n"):
        raise PackUnavailableError(
            f"Demographics resource {filename!r} is a Git LFS pointer; "
            "fetch the optional full pack or explicitly choose 'sample'"
        )
    return yaml.safe_load(text)


def load_pack(pack: Literal["sample", "full"]) -> DemographicPack:
    """Load exactly the selected pack; no fallback or Singleton registration."""
    if pack not in ("sample", "full"):
        raise ValueError(f"Unknown demographics pack: {pack!r}")
    metadata = PackMetadata.model_validate(_read_yaml(f"{pack}_metadata.yaml"))
    if metadata.label != pack:
        raise ValueError(f"Metadata label does not match requested pack {pack!r}")
    return parse_pack(
        metadata,
        _read_yaml("nationalities.yaml"),
        _read_yaml("sample_names.yaml" if pack == "sample" else "world_names.yaml"),
    )


def register_pack(pack: DemographicPack) -> None:
    """Install explicit definitions, reusing equal values and rejecting collisions.

    Definitions are compared as local field snapshots, never as persistence forms.
    This does not add scoped overlays; world-visible catalogs remain a later slice.
    """

    def mixture(data: dict[str, int] | None) -> dict[Subtype, int] | None:
        if data is None:
            return None
        return {
            Subtype.get_instance(label) or Subtype(label=label): weight
            for label, weight in data.items()
        }

    for region_data in pack.regions.values():
        countries: set[Country] = set()
        for data in region_data.countries.values():
            eth_mix = mixture(data.eth_mix)
            country = Country.get_instance(data.id)
            if country is None:
                country = Country(
                    label=data.id,
                    name=data.name,
                    demonym=data.demonym,
                    population=data.population,
                    eth_mix=eth_mix,
                )
            elif (country.name, country.demonym, country.population, country.eth_mix_) != (
                data.name, data.demonym, data.population, eth_mix,
            ):
                raise ValueError(f"Conflicting Country definition: {data.id!r}")
            countries.add(country)
        eth_mix = mixture(region_data.eth_mix)
        region = Region.get_instance(region_data.id)
        if region is None:
            Region(
                label=region_data.id,
                name=region_data.name,
                demonym=region_data.demonym,
                eth_mix=eth_mix,
                countries=countries,
            )
        elif (region.name, region.demonym, region.eth_mix, region.countries) != (
            region_data.name, region_data.demonym, eth_mix, countries,
        ):
            raise ValueError(f"Conflicting Region definition: {region_data.id!r}")
    for label, data in pack.names.items():
        bank = NameBank.get_instance(label)
        if bank is None:
            NameBank(label=label, **data.model_dump())
        elif (bank.xx_names, bank.xy_names, bank.surname, bank.xy_surname) != (
            data.female, data.male, data.surname, data.male_surnames,
        ):
            raise ValueError(f"Conflicting NameBank definition: {label!r}")
