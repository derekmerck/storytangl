from __future__ import annotations
from collections import Counter, defaultdict
from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, ValidationError

from scratch.progression.measured_value import MeasuredValue
from scratch.progression.stats import HasStats

Wallet = Counter[str]
StatMap = dict[Enum, MeasuredValue]

Delta = tuple[int, float]  # offset, scale
DeltaMap = dict[Union[str, Enum], Delta]

class SituationalEffect(BaseModel):
    applies_to_tags: set[str] = Field(default_factory=set)

    cost_modifier: DeltaMap = Field(default_factory=dict)
    difficulty_modifier: DeltaMap = Field(default_factory=dict)
    payout_modifier: DeltaMap = Field(default_factory=dict)

    def applicable_to(self, tags: set[str]) -> bool:
        """Check if the effect is applicable to the given tags."""
        return self.applies_to_tags.issubset(tags)


class HasSituationalEffects:
    situational_effects: list[SituationalEffect]


class SituationalEffectHandler:

    @classmethod
    def get_applicable_effects(cls, has_effects: HasSituationalEffects, tags: set[str]) -> list[SituationalEffect]:
        """Get applicable effects for the given tags."""
        return [effect for effect in has_effects.situational_effects if effect.applicable_to(tags)]

    @classmethod
    def _apply_delta_map(cls, values: dict, delta_map: DeltaMap) -> dict:
        """Apply delta map to the given values."""
        res = values.__class__()
        for k, v in values.items():
            offset, scale = delta_map.get(k, (0, 1))
            res[k] = v * scale + offset
        return res

    @classmethod
    def _accumulate_delta_maps(cls, *delta_maps: DeltaMap) -> DeltaMap:
        """Accumulate multiple delta maps into one."""
        res = defaultdict(lambda: [0, 1])
        for delta_map in delta_maps:
            for k, (offset, scale) in delta_map.items():
                res[k][0] += offset
                res[k][1] *= scale
        return dict(res)

    @classmethod
    def apply_delta_maps(cls, values: dict, *delta_maps: DeltaMap) -> dict:
        """Apply multiple delta maps to the given values."""
        if delta_maps:
            delta_map = cls._accumulate_delta_maps(*delta_maps)
            return cls._apply_delta_map(values, delta_map)
        return values



class Task(BaseModel):
    cost: Wallet
    difficulty: StatMap
    payout: Wallet
    history: list[tuple] = Field(default_factory=list)
    tags: set[str] = Field(default_factory=set)

    def available_for(self, tasker: Tasker) -> bool:
        """Check if the task is available for the given tasker."""
        return True


class Tasker(HasStats):
    wallet: Wallet = Field(default_factory=Counter)


class TaskHandler:

    @classmethod
    def gather_effects(cls, task: Task, tasker: Tasker) -> list[SituationalEffect]:
        """Gather all situational effects for the task and tasker."""
        effects = SituationalEffectHandler.get_applicable_effects(task.situational_effects, tasker.tags)
        effects.extend( SituationalEffectHandler.get_applicable_effects(tasker.situational_effects, task.tags))
        # todo: check for global effects as well
        return effects

    # Cost-related
    @classmethod
    def apply_cost_effects(cls, cost: Wallet, effects: list[SituationalEffect] = None) -> Wallet:
        """Calculate the modified cost of a task for a tasker considering situational effects."""
        if effects:
            cost_modifiers = [e.cost_modifier for e in effects]
            return SituationalEffectHandler.apply_delta_maps(cost, *cost_modifiers)
        return cost

    @classmethod
    def can_pay_cost(cls, cost: Wallet, available: Wallet) -> bool:
        """Check if the available resources are sufficient to cover the cost."""
        return all(available[resource] >= amount for resource, amount in cost.items())

    @classmethod
    def pay_cost(cls, cost: Wallet, available: Wallet):
        """Deduct the cost from the available resources."""
        available.subtract(cost)

    # Difficulty-related
    @classmethod
    def apply_difficulty_effects(cls, difficulty: StatMap, effects: list[SituationalEffect] = None) -> StatMap:
        """Calculate the modified difficulty of a task for a tasker considering situational effects."""
        if effects:
            difficulty_modifiers = [e.difficulty_modifier for e in effects]
            return SituationalEffectHandler.apply_delta_maps(difficulty, *difficulty_modifiers)
        return difficulty

    @classmethod
    def test_difficulty(cls, difficulty: StatMap, tasker_stats: StatMap) -> MeasuredValue:
        """Simulate a difficulty test and return the result."""
        # TODO: Implement a proper likelihood distribution for difficulty testing
        return MeasuredValue(3)  # 'ok' result for testing

    # Payout-related
    @classmethod
    def apply_payout_effects(cls, payout: Wallet, task_result: MeasuredValue,
                             effects: list[SituationalEffect] = None) -> Wallet:
        """Calculate the modified payout of a task for a tasker considering situational effects and task result."""
        if effects:
            payout_modifiers = [e.payout_modifier for e in effects]
            modified_payout = SituationalEffectHandler.apply_delta_maps(payout, *payout_modifiers)
        else:
            modified_payout = payout
        # todo: account for task result quality, if relevant
        return modified_payout

    @classmethod
    def receive_payout(cls, payout: Wallet, payee: Wallet):
        """Add the payout to the payee's wallet."""
        payee.update(payout)

    @classmethod
    def do_task(cls, task: Task, tasker: Tasker):
        """Execute the task for the tasker, including cost payment, difficulty test, and payout."""
        effects = cls.gather_effects(task, tasker)

        # Pay cost
        modified_cost = cls.apply_cost_effects(task.cost, effects)
        if not cls.can_pay_cost(modified_cost, tasker.wallet):
            raise ValueError("Insufficient resources")
        cls.pay_cost(modified_cost, tasker.wallet)

        # Test difficulty
        modified_difficulty = cls.apply_difficulty_effects(task.difficulty, effects)
        task_result = cls.test_difficulty(modified_difficulty, tasker.stats)

        # Receive payout
        modified_payout = cls.apply_payout_effects(task.payout, task_result, effects)
        cls.receive_payout(modified_payout, tasker.wallet)

        # Record task history
        task_summary = (modified_cost, modified_difficulty, task_result, modified_payout)
        task.history.append(task_summary)


    # @staticmethod
    # def test_difficulty(task: Task, tasker: 'Tasker') -> Measure:
    #     total_diff = sum(stat.value - tasker.stats[domain].value for domain, stat in task.difficulty.items())
    #     mean_diff = total_diff / len(task.difficulty)
    #     if mean_diff <= 0:
    #         return Measure.HIGH
    #     elif mean_diff < 5:
    #         return Measure.MEDIUM
    #     elif mean_diff < 10:
    #         return Measure.LOW
    #     else:
    #         return Measure.VERY_LOW
    # 
    # @staticmethod
    # def do_task(task: Task, tasker: 'Tasker'):
    #     task = TaskHandler.apply_situational_effects(task, tasker)
    #     TaskHandler.pay_cost(tasker, task.cost)
    #     difficulty_result = TaskHandler.test_difficulty(task, tasker)
    # 
    #     # Simulate outcome based on difficulty result
    #     outcome = difficulty_result if random.random() < 0.5 else Measure.LOW
    # 
    #     if outcome >= Measure.MEDIUM:
    #         TaskHandler.give_payout(tasker, task.payout)
    #         task.history.append({"result": "success", "outcome": outcome, "payout": task.payout})
    #     else:
    #         task.history.append({"result": "failure", "outcome": outcome, "payout": Wallet()})
# 
# # Example usage
# sword_effect = SituationalEffect(
#     applies_to_tags={"fight"},
#     difficulty_modifier={"strength": Stat(2.0, LogarithmicStatHandler())}
# )
# 
# tasker = Tasker(
#     wallet=Wallet(stamina=10, wit=5),
#     stats={"strength": Stat(5.0, LogarithmicStatHandler()), "intelligence": Stat(8.0, NormalDistributionStatHandler())},
#     situational_effects=[sword_effect]
# )
# 
# fight_task = Task(
#     cost=Wallet(stamina=2),
#     difficulty={"strength": Stat(6.0, LogarithmicStatHandler())},
#     payout=Wallet(hp=5),
#     tags=["fight"]
# )
# 
# TaskHandler.do_task(fight_task, tasker)
# print(fight_task.history)
