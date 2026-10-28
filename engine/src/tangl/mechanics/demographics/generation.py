"""Explicit UPDATE completion for already materialized, world-owned individuals."""
from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from tangl.core.bases import Unstructurable
from tangl.lang.age_range import AgeRange
from tangl.lang.gens import Gens
from tangl.lang.personal_name import PersonalName
from tangl.vm import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx

from .data_models import Country, NameBank, Region
from .demographic import DemographicData
from .sampler import _sample_part
from .selection import Origin, select_bank, select_origin


class GenerationRequest(Unstructurable):
    """Only listed dimensions are requested; name form and bank policy are explicit."""

    model_config = ConfigDict(extra="forbid")

    facts: set[Literal["region", "country", "subtype", "gender", "age_range"]] = Field(
        default_factory=set, json_schema_extra={"include": True},
    )
    name_parts: dict[Literal["given_name", "family_name"], bool] = Field(
        default_factory=dict, json_schema_extra={"include": True},
    )
    bank: str | None = None
    fallback_bank: str | None = None
    origin: Origin | None = Field(default=None, json_schema_extra={"unstructurable": True})
    form: str | None = None
    population_weighted: bool = True


class GenerationReceipt(Unstructurable):
    """Completion and provenance only; never another copy of the individual's name."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    generated: list[str]
    origin: str | None = None
    bank: NameBank | None = Field(default=None, json_schema_extra={"unstructurable": True})
    form: str | None = None
    revision: str | None = None


def complete_generation(
    request: GenerationRequest,
    *,
    personal_name: PersonalName | None,
    demographic: DemographicData,
    receipt: GenerationReceipt | None,
    ctx: PhaseCtx,
) -> tuple[PersonalName | None, DemographicData, GenerationReceipt]:
    """Return values for one world UPDATE commit; completed requests do nothing.

    Draw order: region, country, subtype, gender, age, bank mixture, given, family.
    Every collection is label-sorted; age aliases have one slot per enum value.
    Name request flags are durable: true fills missing values, false preserves absence.
    """
    if receipt is not None:
        return personal_name, demographic, receipt
    if ctx.current_phase is not ResolutionPhase.UPDATE:
        raise ValueError("Demographic generation is supported only during UPDATE")
    if request.origin is not None and request.bank is not None:
        raise ValueError("Choose an origin mixture or an exact bank, not both")
    if request.origin is not None and request.fallback_bank is not None:
        raise ValueError("Fallback applies only to an exact bank request")
    if demographic.country is not None and demographic.region is not None:
        if demographic.country.region is not demographic.region:
            raise ValueError("Country and region constraints contradict one another")
    if "subtype" in request.facts and demographic.subtype is None:
        if (demographic.country is None and demographic.region is None
                and "country" not in request.facts):
            raise ValueError("Subtype generation requires country or region constraints")

    if ("region" in request.facts and demographic.region is None
            and demographic.country is not None):
        if demographic.country.region is None:
            raise LookupError("Country has no declared region")

    current = ({"given_name": personal_name.given_name, "family_name": personal_name.family_name}
               if personal_name is not None else {"given_name": None, "family_name": None})
    missing = {field for field, fill in request.name_parts.items() if fill and current[field] is None}
    if "subtype" in request.facts and demographic.subtype is None:
        if (demographic.country is not None and demographic.country.eth_mix_ is None
                and demographic.country.region is None):
            raise ValueError("Country has no declared subtype mixture")
    catalogs = ctx.get_token_catalogs()
    banks: list[NameBank] = []
    if missing:
        if request.form is None:
            raise ValueError("Requested name parts require an explicit form")
        if request.origin is not None:
            for ref in sorted(request.origin.banks):
                banks.append(select_bank(ref, catalogs=catalogs))
            if not any(weight > 0 for weight in request.origin.banks.values()):
                raise ValueError("Origin requires positive eligible weight")
        elif request.bank is not None:
            try:
                banks = [select_bank(request.bank, catalogs=catalogs)]
            except LookupError:
                if request.fallback_bank is None:
                    raise
                banks = [select_bank(request.fallback_bank, catalogs=catalogs)]
        else:
            raise ValueError("Requested name parts require an explicit bank or origin")
        for bank in banks:
            if request.form not in bank.forms:
                raise LookupError(f"Bank {bank.label!r} has no form {request.form!r}")

    region_choices = sorted(
        (region for region in Region.all_instances()
         if region.countries or "country" not in request.facts),
        key=lambda value: value.label,
    )
    country_choices = sorted(
        demographic.region.countries if demographic.region is not None else Country.all_instances(),
        key=lambda value: value.label,
    )
    if "region" in request.facts and demographic.region is None and not region_choices:
        raise LookupError("No eligible regions")
    if "country" in request.facts and demographic.country is None and not country_choices:
        raise LookupError("No eligible countries")
    # Work on detached values; failures never partly overwrite the owned profile/name.
    profile = demographic.evolve()
    rng = ctx.get_random()
    generated: list[str] = []

    def choose[T: (Region, Country)](values: list[T]) -> T:
        if request.population_weighted:
            weights = [value.population for value in values]
            if not any(weight > 0 for weight in weights):
                raise ValueError("Population selection requires positive weight")
            return rng.choices(values, weights=weights, k=1)[0]
        return rng.choice(values)

    if "region" in request.facts and profile.region is None:
        profile.region = profile.country.region if profile.country is not None else choose(region_choices)
        generated.append("region")
    if "country" in request.facts and profile.country is None:
        choices = (sorted(profile.region.countries, key=lambda value: value.label)
                   if profile.region is not None else country_choices)
        profile.country = choose(choices)
        generated.append("country")
    if "subtype" in request.facts and profile.subtype is None:
        mix = profile.country.eth_mix if profile.country is not None else profile.region.eth_mix
        candidates = sorted(mix, key=lambda value: value.label)
        profile.subtype = rng.choices(candidates, weights=[mix[value] for value in candidates], k=1)[0]
        generated.append("subtype")
    if "gender" in request.facts and profile.gender is None:
        profile.gender = rng.choice([Gens.XX, Gens.XY])
        generated.append("gender")
    if "age_range" in request.facts and profile.age_range is None:
        profile.age_range = rng.choice(list(AgeRange))
        generated.append("age_range")

    eligible_banks = (
        [bank for (_ref, weight), bank in zip(sorted(request.origin.banks.items()), banks, strict=True)
         if weight > 0] if request.origin is not None and banks else banks
    )
    active = any(
        ("given_name" in missing and bank.forms[request.form].given is not None)
        or ("family_name" in missing and bank.forms[request.form].family is not None)
        for bank in eligible_banks
    )
    selected: NameBank | None = None
    name = personal_name
    if active:
        selected = (select_origin(request.origin, catalogs=catalogs, rng=rng).bank
                    if request.origin is not None else banks[0])
        form = selected.forms[request.form]
        updates: dict[str, str] = {}
        for field, part in (("given_name", form.given), ("family_name", form.family)):
            if field in missing and part is not None:
                updates[field] = _sample_part(part, rng)
                generated.append(field)
        if updates:
            name = personal_name.evolve(**updates) if personal_name is not None else PersonalName(
                **updates, title="", gender=Gens.X_,
            )
    return name, profile, GenerationReceipt(
        generated=generated, origin=request.origin.label if request.origin else None,
        bank=selected, form=request.form if selected else None,
        revision=selected.revision if selected else None,
    )
