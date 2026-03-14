from __future__ import annotations

from typing import Any

from tangl.core import HasNamespace, contribute_ns
from tangl.lang.personal_name import PersonalName
from tangl.lang.gens import Gens as Gender
from tangl.lang.age_range import AgeRange
from .data_models import Country, Region, Subtype


class DemographicData(PersonalName):
    """DemographicData()

    Lightweight runtime profile describing an entity's sampled or authored
    demographic identity.

    Why
    ----
    ``DemographicData`` packages the naming and profile attributes that
    mechanics facets can publish into story namespaces or adapt into richer
    prose and media later on.
    """

    given_name: str
    family_name: str
    gender: Gender = Gender.XX
    subtype: Subtype = None
    country: Country = None
    region: Region = None
    age_range: AgeRange = None

    # todo: set family_name_first from country/language

    @property
    def demonym(self) -> str:
        if self.region and self.region.demonym:
            return self.region.demonym              # "east asian", "north american"
        if self.country and self.country.demonym:
            return self.country.demonym             # "chinese", "american"
        if self.subtype and self.subtype.demonym:
            return self.subtype.demonym             # "han", "african-american"
        return ""


class HasDemographics(HasNamespace):
    """HasDemographics()

    Thin author-facing facet for entities that expose demographic identity.

    Why
    ----
    ``HasDemographics`` keeps the author surface mixin-friendly while treating
    demographic data as a profile/domain facet rather than a standalone random
    helper library.

    Key Features
    ------------
    - Stores a :class:`DemographicData` profile on the owning entity.
    - Publishes demographic symbols through the standard local namespace
      contract so story roles can expose keys like ``guide_full_name``.
    - Uses demographic naming as a fallback while preserving an explicitly set
      ``name`` field on richer story nodes when present.
    """

    demographic: DemographicData

    @property
    def name(self) -> str:
        explicit_name = self.__dict__.get("name")
        if isinstance(explicit_name, str) and explicit_name:
            return explicit_name
        return self.demographic.name()

    @property
    def demographics(self) -> DemographicData:
        """Compatibility alias using the family-oriented plural surface."""
        return self.demographic

    @property
    def familiar_name(self) -> str:
        return self.demographic.familiar_name()

    @property
    def formal_name(self) -> str:
        # todo: Need to inject title from parent's role association
        return self.demographic.formal_name()

    @property
    def full_name(self) -> str:
        return self.demographic.full_name()

    @property
    def familiar_full_name(self) -> str:
        return self.demographic.familiar_full_name()

    @property
    def formal_full_name(self) -> str:
        # todo: Need to inject title from parent's role association
        return self.demographic.formal_full_name()

    @contribute_ns
    def provide_demographic_symbols(self) -> dict[str, Any]:
        """Publish demographic profile data into the local namespace."""
        payload: dict[str, Any] = {
            "demographic": self.demographic,
            "given_name": self.demographic.given_name,
            "family_name": self.demographic.family_name,
            "full_name": self.full_name,
            "familiar_name": self.familiar_name,
            "formal_name": self.formal_name,
            "familiar_full_name": self.familiar_full_name,
            "formal_full_name": self.formal_full_name,
            "demonym": self.demographic.demonym,
        }

        if self.demographic.gender is not None:
            payload["gender"] = self.demographic.gender
        if self.demographic.age_range is not None:
            payload["age_range"] = self.demographic.age_range
        if self.demographic.region is not None:
            payload["region"] = self.demographic.region
        if self.demographic.country is not None:
            payload["country"] = self.demographic.country
        if self.demographic.subtype is not None:
            payload["subtype"] = self.demographic.subtype

        return payload


HasDemographic = HasDemographics
