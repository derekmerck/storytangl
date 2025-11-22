from __future__ import annotations
from collections import Counter

from pydantic import Field

from tangl.exceptions import TradeHandlerError
from tangl.entity.mixins import HasNamespace, NamespaceHandler, AvailabilityHandler, Conditional, ConditionHandler
from .measures import Quality
from .stat_domain_map import StatDomainMap, HasStats

# from .situational_effect import SituationalEffect, HasSituationalEffects
SituationalEffect = HasSituationalEffects = object

Tasker = HasStats  # also HasWallet, HasSituationalEffects
Wallet = Counter


class TaskHandler:
    """
    An TaskHandler is similar to a GameHandler.  It is called on entering an Activity
    node to evaluate that activities task relative to the activating tasker.
    """
    # -----------------
    # Weighted props
    # -----------------

    @classmethod
    def cost_for(cls, task: Task, effects = None) -> Wallet:
        """Compute situational cost"""
        # todo: cost weighted by situational effects
        return task.cost

    @classmethod
    def difficulty_for(cls, task: Task, effects = None) -> StatDomainMap:
        """Compute situational difficulty"""
        # todo: difficulty weighted by situational effects
        return task.difficulty

    @classmethod
    def difficulty_delta(cls, difficulty: StatDomainMap, tasker_stats: StatDomainMap) -> Quality:
        """Compute situational difficulty delta relative to tasker stats"""
        difficulty_delta = StatDomainMap.delta(difficulty, tasker_stats)
        return difficulty_delta

    @classmethod
    def payout_for(cls, task: Task, effects = None) -> Wallet:
        """Compute situational payout"""
        # todo: payout weighted by situational effects
        return task.payout

    @classmethod
    def realized_payout(cls, payout: Wallet, outcome: Quality) -> Wallet:
        """Compute realized payout based on task outcome"""
        # todo: payout weighted by outcome, maybe using the exp2 weighting?
        return payout

    # -----------------
    # Checks
    # -----------------

    @classmethod
    def can_pay_cost(cls, task: Task, tasker: Tasker) -> bool:
        applicable_effects = cls.get_applicable_effects(task, tasker)
        cost = cls.cost_for(task, applicable_effects)
        return tasker.can_lose(**cost)

    @classmethod
    def can_receive_payout(cls, task: Task, tasker: Tasker) -> bool:
        applicable_effects = cls.get_applicable_effects(task, tasker)
        payout = cls.payout_for(task, applicable_effects)
        return tasker.can_gain(**payout)

    # -----------------
    # Actions
    # -----------------

    @classmethod
    def pay_cost(cls, tasker: Tasker, cost: Wallet):
        tasker.lose(**cost)

    @classmethod
    def test_difficulty(cls, tasker: HasStats, difficulty: StatDomainMap) -> Quality:
        difficulty_delta = cls.difficulty_delta(difficulty, tasker.stats)
        # todo: transform to outcome randomly according to probability dist or variance ...
        return difficulty_delta

    @classmethod
    def receive_payout(cls, tasker: Tasker, payout: Wallet):
        tasker.gain(**payout)

    # -----------------
    # Bookkeeping
    # -----------------

    @classmethod
    def _update_task_history(cls, task: Task, difficulty: StatDomainMap, outcome: Quality, payout: Wallet):
        update = (difficulty, outcome, payout)
        task.history.append( update )

    # -----------------
    # Entry point
    # -----------------

    @classmethod
    def do_task(cls, task: Task, tasker: Tasker):
        applicable_effects = cls.get_applicable_effects(task, tasker)

        cost = cls.cost_for(task, effects=applicable_effects)
        difficulty = cls.difficulty_for(task, effects=applicable_effects)
        payout = cls.payout_for(task, effects=applicable_effects)

        if not tasker.can_lose(**cost):
            raise TradeHandlerError
        cls.pay_cost(tasker, cost)

        outcome = cls.test_difficulty(tasker, difficulty)
        if outcome >= Quality.AVERAGE:
            payout = cls.realized_payout(payout, outcome)
            cls.receive_payout(tasker, payout)
        else:
            payout = None

        cls._update_task_history(difficulty, outcome, payout)

    @classmethod
    def get_applicable_effects(cls, task: Task, tasker: Tasker) -> set[SituationalEffect]:
        # Not active right now
        # return SituationalEffectHandler.get_applicable_effects_for(task, tasker)
        pass

# todo: mixin Conditional, HasSituationalEffects
class Task(HasNamespace):
    """
    A Task is a similar to a single-round solitaire Game.
    """
    # conditions might be 'has appropriate outfit' or min stats

    history: list = Field(default_factory=list)

    cost: Wallet = Field(..., validate_default=True)
    difficulty: StatDomainMap = Field(..., validate_default=True)
    payout: Wallet = Field(..., validate_default=True)

    # todo: is there a way in pydantic to attach converters to an annotated type?

    # @field_validator('difficulty')
    # @classmethod
    # def _convert_to_statmap(cls, data):
    #     return data
    #
    # @field_validator('cost', 'payout')
    # @classmethod
    # def _convert_to_wallet(cls, data):
    #     return data

    # @AvailabilityHandler.strategy
    # def _check_conditions(self, tasker: HasStats):
    #     # todo: overwrite the regular conditional check with satisified_by for this?
    #     #    or just put tasker in the namespace and let the conditions refer to them?
    #     ConditionHandler.check_conditions_satisfied_by(self.conditions, tasker)

    def cost_for(self, tasker: HasStats) -> Wallet:
        return TaskHandler.cost_for(self, tasker)

    def difficulty_for(self, tasker: HasStats) -> StatDomainMap:
        return TaskHandler.difficulty_for(self, tasker)

    def payout_for(self, tasker: HasStats) -> Wallet:
        return TaskHandler.payout_for(self, tasker)

    def can_pay_cost(self, tasker: HasStats) -> bool:
        return TaskHandler.can_pay_cost(self, tasker)

    def can_receive_payout(self, tasker: HasStats) -> bool:
        return TaskHandler.can_receive_payout(self, tasker)

    def do_task(self, tasker: HasStats):
        # todo: invoke on enter, how do we assign the tasker tho?
        TaskHandler.do_task(self, tasker)

    @NamespaceHandler.strategy
    def _add_task_result(self):
        if self.history:
            return {'task': self.history[-1]}
