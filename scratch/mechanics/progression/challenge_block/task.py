from __future__ import annotations
import types

from pydantic import BaseModel, Field

from tangl.core.services import BaseHandler
from tangl.core import Entity
from tangl.core import AvailabilityHandler
from tangl.story.asset import Wallet, HasWallet
from tangl.mechanics.stats.stat_test import StatTest

Transaction = object
Quality = types.SimpleNamespace()

# todo: Tasks and games could probably be wrapped singleton nodes, the only reason to make them nodes at all is so that they can be attached to story graphs.  However, the wrapping block already takes care of all the visit bookkeeping.

class TaskHandler(BaseHandler):
    ...

class Task(Entity):

    cost: Transaction = None
    reward: Transaction = None
    stat_test: StatTest = Field(default_factory=StatTest)

    @AvailabilityHandler.strategy
    def _can_afford(self, tasker: Tasker) -> bool:
        return tasker.can_afford(self.cost)

class Tasker(HasWallet, Entity):
    ...
