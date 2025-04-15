from pydantic import BaseModel

from tangl.narrative.lang.personal_name import PersonalName
from .data_models import Subtype, Country, Region, NameBank
from tangl.narrative.lang.gens import Gens as Gender
from tangl.narrative.lang.age_range import AgeRange


class DemographicData(PersonalName):

    given_name: str
    family_name: str
    gender: Gender = None
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


class HasDemographic(BaseModel):
    # todo: re find any pn.aka or pronoun from template actor in text, and
    #       flag it as belonging to _this_ actor with name-type

    demographic: DemographicData

    @property
    def name(self):
        return self.demographic.name()

    @property
    def familiar_name(self):
        return self.demographic.familiar_name()

    @property
    def formal_name(self):
        # todo: Need to inject title from parent's role association
        return self.demographic.formal_name()

    @property
    def full_name(self):
        return self.demographic.full_name()

    @property
    def familiar_full_name(self):
        return self.demographic.familiar_full_name()

    @property
    def formal_full_name(self):
        # todo: Need to inject title from parent's role association
        return self.demographic.formal_full_name()
