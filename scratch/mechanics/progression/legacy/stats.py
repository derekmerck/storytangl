from typing import Protocol
from enum import Enum, auto, IntEnum
from typing import Type, ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from scratch.progression.measured_value import MeasuredValue, MeasuredValueHandler


class StatDomain(Protocol):

    stat_handler: Optional[Type[MeasuredValueHandler]]
    stat_measure: Optional[Type[IntEnum]]
    stat_currency: str


StatMap = dict[Enum, MeasuredValue]

class HasStats(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)
    stat_domains: ClassVar[Type[Enum | StatDomain]] = None
    stats: StatMap = Field(None, validate_default=True)

    @field_validator("stats", mode="before")
    @classmethod
    def _initialize_stats(cls, data):
        if isinstance(data, dict):
            # accepts dict { stat_name: mv-like }
            _data = {}
            for domain, mv in data.items():
                if not isinstance(domain, cls.stat_domains):
                    domain = cls.stat_domains(domain)
                mv = MeasuredValue(mv, handler=domain.stat_handler, measure=domain.stat_measure)
                _data[domain] = mv
            # todo: check for skipped domains
            data = _data
        elif isinstance(data, list):
            # accepts list [ mv-like ]
            _data = {}
            for domain, mv in zip(cls.stat_domains, data):
                mv = MeasuredValue(mv, handler=domain.stat_handler, measure=domain.stat_measure)
                _data[domain] = mv
            data = _data
        elif not data:
            data = {}
            for domain in cls.stat_domains:
                data[domain] = MeasuredValue(3, handler=domain.stat_handler, measure=domain.stat_measure)
        return data

    # delegate stat-names to stats
    def __getattr__(self, item):
        if x := self.stat_domains(item):
            return self.stats[x]
        return super().__getattr__(item)

    def __setattr__(self, key, value):
        if x := self.stat_domains(key):
            self.stats[x] = value
            return
        super().__setattr__(key, value)
