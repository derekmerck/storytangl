from __future__ import annotations

from pydantic import ConfigDict, Field

from tangl.core import HasNamespace, contribute_ns
from tangl.core.bases import Unstructurable
from tangl.lang.age_range import AgeRange
from tangl.lang.gens import Gens as Gender

from .data_models import Country, Region, Subtype


class DemographicData(Unstructurable):
    """Owned demographic facts; personal names belong to the actor's prose field."""

    model_config = ConfigDict(extra="forbid")

    gender: Gender | None = None
    age_range: AgeRange | None = None
    subtype: Subtype | None = Field(default=None, json_schema_extra={"unstructurable": True})
    country: Country | None = Field(default=None, json_schema_extra={"unstructurable": True})
    region: Region | None = Field(default=None, json_schema_extra={"unstructurable": True})

    @property
    def demonym(self) -> str:
        if self.region and self.region.demonym:
            return self.region.demonym
        if self.country and self.country.demonym:
            return self.country.demonym
        if self.subtype and self.subtype.demonym:
            return self.subtype.demonym
        return ""


class HasDemographics(HasNamespace):
    """Publish profile facts without owning, copying, or projecting a personal name."""

    demographic: DemographicData = Field(
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @contribute_ns
    def provide_demographic_symbols(self) -> dict[str, object]:
        profile = self.demographic
        facts = {
            "gender": profile.gender,
            "age_range": profile.age_range,
            "region": profile.region,
            "country": profile.country,
            "subtype": profile.subtype,
        }
        return {
            "demographic": profile,
            "demonym": profile.demonym,
            **{key: value for key, value in facts.items() if value is not None},
        }
