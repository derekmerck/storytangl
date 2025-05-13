from enum import Enum
from functools import total_ordering
from typing import Any, Callable, Dict, Optional

from .entity import Entity

class Phase(str, Enum):
    INIT = "init"            # graph created
    ENTER = "enter"          # cursor moved  :todo: is this a phase or a group of phases
    RESOLVE = "resolve"      # figure out what is here, what is active (resolved != actionable)
    REDIRECTS = "redirect"   # check for auto-redirects
    EFFECT = "effect"        # bookkeeping and state mutation
    RENDER = "render"        # produce content
    PROJECT = "project"      # convert content into journal fragments
    CONTINUES = "continues"  # check for auto-continue

@total_ordering
class Capability(Entity):
    phase: Phase
    priority: int = 0
    predicate: Optional[Callable[[Dict[str, Any]], bool]] = None
    # todo: is this a predicate(ctx) or a match(entity) criteria?  A scoped object with these criteria
    #       can use this capability, or a context map confirms that this capability exists?
    apply: Callable[..., Any] = lambda *a, **kw: None

    def __call__(self, *args, **kwargs):
        return self.apply(*args, **kwargs)

    def __lt__(self, other): return self.priority < other.priority
    # todo: is the sortkey actually self.phase, self.priority where phases are ordered?
    #       would we ever compare caps from two different phases?  should we catch if its tried?

    def should_run(self, ctx: Dict[str, Any]) -> bool:
        return not self.predicate or self.predicate(ctx)
