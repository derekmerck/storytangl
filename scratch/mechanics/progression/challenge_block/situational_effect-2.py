from __future__ import annotations
from typing import TYPE_CHECKING
from collections import Counter

from pydantic import Field

from tangl.entity.mixins import Lockable, Conditional
from tangl.graph import Node
from tangl.graph.mixins import WrappedSingleton
from tangl.type_hints import Tags
from tangl.exceptions import TradeHandlerError
from .stat_domain_map import StatDomainMap, HasStats

if TYPE_CHECKING:
    from .task import Task, Tasker

Wallet = Counter

class SituationalEffectHandler:

    @classmethod
    def applicable_to(cls, situational_effect: SituationalEffect, node: Node) -> bool:
        return situational_effect.applies_to_tags.issubset(node.tags)

    @classmethod
    def get_applicable_effects_between(cls, task, tasker) -> set[SituationalEffect]:
        res = set()
        res.update([e for e in tasker.situational_effects if cls.applicable_to(e, task)])
        res.update([e for e in task.situational_effects if cls.applicable_to(e, tasker)])
        # check for active global effects in the story
        global_effects = tasker.graph.find_nodes(types=GlobalEffect)  # type: list[GlobalEffect]
        res.update([e for e in global_effects if e.applicable_to(tasker) and e.applicable_to(task)])
        return res

class SituationalEffect:
    """
    Think of this as a 'task delta'.  It is composed with tasks before they are evaluated.

    We can also think about it as a matrix modifier for the difficulty stat vector being
    measured against the input stat vector.

    originally wanted to keep costs, difficulties, outcomes _all_ as stats/stat deltas.
    """

    applies_to_tags: Tags = Field(default_factory=set)

    cost_modifier: Wallet = Field(..., validate_default=True)
    difficulty_modifier: StatDomainMap = Field(..., validate_default=True)
    payout_modifier: Wallet = Field(..., validate_default=True)


    def applicable_to(self, node: Node) -> bool:
        return SituationalEffectHandler.applicable_to(self, node)

    def apply(self, task: Task, **kwargs):
        return NotImplemented


class HasSituationalEffects:

    _situational_effects: list[SituationalEffect] = Field(default_factory=list)

    @property
    def situational_effects(self) -> list[SituationalEffect]:
        # override this to access effects on badges, items, etc.
        return self._situational_effects

    def get_applicable_situational_effects(self, task: Task):
        return [ x for x in self.situational_effects if x.applicable_to(task) ]


class GlobalEffectType(Lockable, Conditional):
    """
    A global effect is a _conditional_ situational effect that is applicable
    throughout a story while it is active.  It does not need to be bound to a
    particular activator or activity.

    Unlike situational effects, it is _not_ a singleton, it is an instance variable
    that _wraps_ a singleton situational effect and provides an on/off switch.

    If it has conditions, it is activated when those conditions are satisfied
    _and_ it is marked active.  If it has no conditions, it is active while it
    is manually activated.

    While active, a global effect will be applied to all nodes that meet its
    tag requirements.
    """

    situational_effect: SituationalEffect = None
    _active: bool = Field(False, json_schema_extra={'instance_var': True})

    # Global effects can have activation costs and other usage costs, but
    # those aspects are too specific to model here, so deferred to subclassing.

    activation_cost: Wallet = None
    maintenance_cost: Wallet = None
    usage_cost: Wallet = None
    deactivation_cost: Wallet = None

    @property
    def active(self):
        return self._active

    def activate(self, tasker: Tasker) -> bool:
        if self.activation_cost:
            if tasker.can_afford(self.activation_cost):
                tasker.pay_cost(self.activation_cost)
            else:
                raise TradeHandlerError(f'Cannot pay activation cost for {self}')
        self._active = True

    def deactivate(self):
        self._active = False

    def applicable_to(self, node: Node) -> bool:
        if self.active and self.situational_effect.applicable_to( node ):
            return True
        return False

GlobalEffect = WrappedSingleton.create_wrapper_cls(GlobalEffectType)

# Old effect-based weighting...
# @staticmethod
# def weighted_value(value: Stat, *modifiers: Stat) -> Stat:
#     res = value
#     for m in modifiers:
#         res = res * m
#     return res
#
# @property
# def weighted_cost(self) -> Stat:
#     cost_modifiers = [ e.cost_modifier for e in self.get_applicable_effects() ]
#     return self.weighted_value(self.activity.cost, *cost_modifiers)
#
# @property
# def weighted_difficulty(self) -> Stat:
#     difficulty_modifiers = [ e.difficulty_modifier for e in self.get_applicable_effects() ]
#     return self.weighted_value(self.activity.cost, *difficulty_modifiers)
#
# @property
# def weighted_outcome(self) -> Stat:
#     outcome_modifiers = [ e.outcome_modifier for e in self.get_applicable_effects() ]
#     return self.weighted_value(self.activity.cost, *outcome_modifiers)
