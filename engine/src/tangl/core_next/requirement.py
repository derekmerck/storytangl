from typing import ClassVar, Callable

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

@dataclass
class ProvisionKey:
    domain: str  # todo: going to get this confused with graph-domain/templates
    name: str
    def __hash__(self): return hash((self.domain, self.name))

    def __repr__(self):
        return f"{self.domain}:{self.name}"

@dataclass
class Requirement:
    key: ProvisionKey
    strategy: str = "direct"      # lookup in scope tiers
    params: dict = Field(default_factory=dict)
    tier: str | None = None       # override starting tier (optional)

    def __hash__(self): return hash((self.key, self.strategy, *self.params.items(), self.tier))

    # registry for strategy functions
    _strategies: ClassVar[dict[str, Callable]] = {}

    @classmethod
    def register_strategy(cls, name):
        def deco(fn):
            cls._strategies[name] = fn
            return fn
        return deco

    # -- two canonical hooks used by Resolver --
    def select_candidates(self, node, graph, ctx):
        if self.strategy not in self._strategies:
            raise ValueError(f"Strategy '{self.strategy}' not found, must be one of {list(self._strategies.keys())}")
        fn = self._strategies[self.strategy]
        yield from fn("select", self, node, graph, ctx)

    def maybe_create(self, node, graph, templates, ctx):
        fn = self._strategies[self.strategy]
        return fn("create", self, node, graph, ctx)

@Requirement.register_strategy("direct")
def select_direct(op, self, node, graph, ctx):
    return []

class Providable(BaseModel):
    requires: set[Requirement] = Field(default_factory=set)
    provides: set[ProvisionKey] = Field(default_factory=set)
