from __future__ import annotations
from typing import Iterable

from tangl.entity.mixins import AvailabilityHandler, RenderHandler, NamespaceHandler
from tangl.mechanics.progression.task import Task, TaskHandler, Tasker
from .block import Block
from .menu import Menu, MenuActionHandler

class ActivityHub(Menu):
    """
    Activity Hubs are menu-blocks for progression mechanic {class}\`.Task\` objects.
    """

    @MenuActionHandler.strategy
    def _get_activities(self):
        return self.activities

    @property
    def activities(self) -> Iterable[Activity]:
        return self.find_children(Activity)


class Activity(Block):
    """
    Activities are block wrappers for progression mechanic {class}\`.Task\` objects.

    Tasks have a cost, a difficulty, and a payout.  If the Tasker can pay the cost,
    they can test against the difficulty measure to get an outcome.  The outcome
    modifies the payout received.

    Activities are subject to SituationalEffects on their Task.
    """

    @property
    def task(self) -> Task:
        return self.find_child(Task)

    @AvailabilityHandler.strategy
    def _check_can_pay(self, tasker: Tasker):
        return TaskHandler.can_afford(self.task, tasker)

    @NamespaceHandler.strategy
    def _include_activity_results(self):
        if self.task.history:
            cost, difficulty, outcome, payout = self.task.history[-1]
            return {
                "task": {
                    "cost": cost,               # paid cost
                    "difficulty": difficulty,   # modified difficulty
                    "outcome": outcome,         # outcome quality
                    "payout": payout            # received payout
                }
            }

    @RenderHandler.strategy
    def _include_activity_result_desc(self):
        ...

    def enter(self, activator: Tasker = None):
        block, update = super().enter()
        if block is not self:
            return block
        self.activity_handler(self, activator).handle_activity()
        # todo: may need to rerender and addend the update

