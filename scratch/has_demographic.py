from __future__ import annotations
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, model_validator, field_validator
from nameparser import HumanName
from nameparser.config import CONSTANTS as HN_CONSTANTS

from tangl.mechanics.look.enums import AgeRange
from tangl.narrative.lang.gens import Gens
from tangl.narrative.lang.gendered_nominals import gn

HN_CONSTANTS.titles.add('boss')

class Demographic(BaseModel, arbitrary_types_allowed=True):
    name: HumanName
    age: AgeRange = AgeRange.MID
    gens: Gens = Gens.XX
    origin: Optional[str] = None  # region or country code
    background: Optional[str] = None

    @field_validator('name', mode='before')
    @classmethod
    def _parse_name(cls, data):
        if not isinstance(data, HumanName):
            data = HumanName(data)
        if not data.title:
            data.title = "mr."
        return data

    @model_validator(mode='after')
    def _set_title(self):
        self.name.title = gn(self.name.title, self.gens.is_xx).capitalize()
        return self

    @property
    def titled_name(self):
        return f"{self.name.title} {self.name.last or self.name.first or self.name.nickname}"

    @property
    def common_name(self):
        return self.name.first or self.titled_name

    @property
    def full_name(self):
        s = f"{self.name.first} {self.name.last}".strip()
        if not s:
            s = self.familiar_name
        return s

    @property
    def formal_name(self):
        s = f"{self.name.title} {self.full_name}"
        if self.name.suffix:
            s += f", {self.name.suffix}"
        return s

    @property
    def familiar_name(self):
        return self.name.nickname or self.common_name


if __name__ == "__main__":

    d = Demographic(name="Prof. John Doe (Jack)")
    assert d.familiar_name == "Jack"

    d = Demographic(name="Mr. John Doe, PhD")
    assert d.formal_name.startswith("Ms.") and d.formal_name.endswith("PhD")
