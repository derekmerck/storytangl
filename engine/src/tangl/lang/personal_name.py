from typing import Self, Literal, Any
from enum import Enum
import logging

from pydantic import BaseModel, Field
from nameparser import HumanName

from tangl.utils.enum_plus import EnumPlusMixin
from .gens import Gens as Gender
from .gendered_nominals import normalize_gn

logger = logging.getLogger(__name__)

# todo: replace 'has_personal_name' with this improved system

class PersonalName(BaseModel):
    """
    Provides methods:
    - `name`, `familiar_name`, `formal_name`: short address
    - `full_name`, `familiar_full_name`, `formal_full_name`: detailed address, falls back to short form
    """

    given_name: str = None
    middle_name: str = None
    family_name: str = None
    title: str = Field(default="mr.")   # this is treated like a gendered nominal
    suffix: str = None
    nickname: str = None  # preferred nick
    aliases: set[str] = Field(default_factory=set)

    gender: Gender = Gender.XX
    family_name_first: bool = False      # False (default) is common western naming order
    # anonymous_nominal_adj: str = ""    # the "blonde" guy, etc.

    def is_xx(self, gender: Gender = None) -> bool:
        if gender and not isinstance(gender, Gender):
            try:
                gender = Gender(gender)
            except ValueError:
                logger.error(f"Invalid gender: {gender}")
                raise
        logger.debug(f"is_xx: {(gender or self.gender).is_xx}")
        return (gender or self.gender).is_xx

    @classmethod
    def from_full_name(cls, full_name: str) -> Self:
        hn = HumanName(full_name=full_name)
        res = cls(given_name=hn.first,
                  middle_name=hn.middle,
                  family_name=hn.last,
                  title=hn.title,
                  suffix=hn.suffix,
                  nickname=hn.nickname)
        return res

    def akas(self):
        return { x for x in
                 [ self.given_name,
                   self.family_name,
                   self.nickname,
                   self.name(),
                   self.familiar_name(),
                   self.formal_name(),
                   self.full_name(),
                   self.familiar_full_name(),
                   self.formal_full_name() ] if x is not None }.union(self.aliases)

    def goes_by(self, alias: str) -> bool:
        return alias in self.akas()

    def get_title(self, gender: Gender = None) -> str:
        if not self.title:
            return ""
        title_ = normalize_gn(self.title, self.is_xx(gender)).capitalize()
        return title_

    def name(self):
        # Commonly addressed as
        if self.given_name:
            return self.given_name       # Jonathan
        elif self.family_name:
            return self.formal_name()    # Mr. Smith
        else:
            return self.familiar_name()  # Jack

    def familiar_name(self) -> str:
        # Familiarly addressed as, ordered least formal to most
        if self.nickname:
            return self.nickname         # Jack
        elif self.given_name:
            return self.given_name       # Jonathan
        elif self.family_name:
            return self.family_name      # Smith
        raise ValueError(f"Unable to determine a familiar name for {self}")

    def formal_name(self) -> str:
        # Formally addressed as, ordered most formal to least

        def _decorate_name(name: str) -> str:
            if self.title:
                name = self.get_title() + " " + name
            return name

        if self.family_name:
            return _decorate_name(self.family_name)   # Mr. Smith
        elif self.given_name:
            return _decorate_name(self.given_name)    # Mr. Jonathan
        elif self.nickname:
            return _decorate_name(self.nickname)      # Mr. Jack
        raise ValueError(f"Unable to determine a familiar name for {self}")

    # --------------------------------

    def get_full_name(self) -> str:
        if self.given_name and self.family_name:
            if self.family_name_first:
                return f"{self.family_name} {self.given_name}"    # Smith Jonathan
            else:
                return f"{self.given_name} {self.family_name}"    # Jonathan Smith

    def get_familiar_full_name(self) -> str:
        if self.nickname and self.family_name:
            if self.family_name_first:
                return f"{self.family_name} {self.nickname}"      # Smith Jack
            else:
                return f"{self.nickname} {self.family_name}"      # Jack Smith

    def full_name(self):
        # Commonly specified as, ordered most formal to least
        if s := self.get_full_name():                              # Jonathan Smith
            return s
        elif s := self.get_familiar_full_name():                   # Jack Smith
            return s
        return self.formal_full_name()                             # Mr. Smith, Mr. Jonathan, Mr. Jack

    def familiar_full_name(self) -> str:
        # Ordered least formal to most, or familiar name
        if s := self.get_familiar_full_name():                      # Jack Smith
            return s
        elif s := self.get_full_name():                             # Jonathan Smith
            return s
        return self.familiar_name()                            # Jack, Jonathan, Smith

    def formal_full_name(self, gender: Gender = None) -> str:
        # Formal titled full_name in most to least formal order

        def _decorate_name(name: str) -> str:
            if self.title:
                name = self.get_title() + " " + name
            if self.suffix:
                name = name + " " + self.suffix
            return name

        if s := self.get_full_name():
            return _decorate_name(s)               # Mr. Jonathan Smith Jr.
        elif s := self.get_familiar_full_name():
            return _decorate_name(s)               # Mr. Jack Smith Jr.
        return self.formal_name()                  # Mr. Smith, Mr. Jonathan, Mr. Jack
