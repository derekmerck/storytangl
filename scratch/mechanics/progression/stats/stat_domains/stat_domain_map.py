from enum import Enum
from typing import ClassVar, Type

from pydantic import field_validator, Field, ConfigDict, model_validator

from tangl.type_hints import UniqueLabel
from tangl.story.asset.fungible import HasWallet
from .stats import Stat, StatHandler
from .domains import PsychosomaticDomains
from .measures import Quality

StatDomains = Enum
StatDomainMap = dict[UniqueLabel, Stat]

# todo: mixin HasSituationalEffects
class HasStats(HasWallet):
    """Mixin for nodes with a stat map"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stat_domains: ClassVar[Type[StatDomains]] = PsychosomaticDomains
    stat_cls: ClassVar[Type[Stat]] = Stat
    stats: StatDomainMap = Field(None, validate_default=True)

    @field_validator('stats', mode='before')
    @classmethod
    def _initialize_stat_domains(cls, data):
        # todo: should accept list/tuple of vals or dict of key: values
        if not data:
            data = [ 3 ] * len(cls.stat_domains)
        stats = { cls.stat_domains(i+1).name.lower(): cls.stat_cls(v) for i, v in enumerate(data) }
        print( 'initial stats', stats )
        return stats

    @model_validator(mode='after')
    def _initialize_currencies(self):
        for k, v in self.stat_domains.stat_currency().items():
            self.wallet[v] = self.stats[k.name.lower()]

    def delta(self, value: StatDomainMap) -> Quality:
        # use average for now
        total_dist = 0.
        for k, v in value.items():
            total_dist += StatHandler.delta(self.stats[k].fv, v)
        average_dist = total_dist / len(value)  # should be 1-20
        return Quality(average_dist)

    def __getattr__(self, item):
        _item = item
        if isinstance(item, Enum):
            _item = item.name
        if isinstance(_item, str):
            _item = _item.lower()
        if x := self.stats.get(_item):
            return x
        return super().__getattr__(item)
