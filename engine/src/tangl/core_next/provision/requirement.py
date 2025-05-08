from typing import ClassVar, Callable
import logging

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProvisionKey:
    domain: str  # todo: going to get this confused with graph-domain/templates
    name: str
    def __hash__(self): return hash((self.domain, self.name))

    def __repr__(self):
        return f"PK({self.domain}:{self.name})"

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
        for ent in self._strategies[self.strategy]("select", self, node, graph, ctx):
            yield ent

    def maybe_create(self, node, graph, ctx):
        fn = self._strategies[self.strategy]
        obj = fn("create", self, node, graph, ctx)
        logger.debug(f"Maybe-created provider {obj}")
        return obj

# requirement.py  ------------------------------------------
@Requirement.register_strategy("direct")
def direct_strategy(phase, req, node, graph, ctx):
    """
    phase == "select"  → yield providers already in graph
    phase == "create"  → if template exists, build it
    """
    from .registry import Registry         # avoid circular import
    from .template import Template

    if phase == "select":
        # breadth: local subtree → graph index
        uids = graph.index.get(req.key, set())
        return [ graph.registry[uid] for uid in uids ]

    elif phase == "create":
        templates: Registry[Template] = ctx.get("templates")
        if not templates:
            return None
        tpl = templates.find_one(provides=req.key)
        logger.debug(f"found template {tpl}")
        if tpl:
            obj = tpl.build(ctx)
            logger.debug(f"created inst {obj}")
            return tpl.build(ctx)


class Providable(BaseModel):
    requires: set[Requirement] = Field(default_factory=set)
    provides: set[ProvisionKey] = Field(default_factory=set)
