from __future__ import annotations

from pydantic import BaseModel, Field

from tangl.type_hints import Tag
from tangl.core import TaskHandler, HandlerPriority
from tangl.core import Entity
from .enums import Difficulty, Quality
from .stat_domain import StatDomain
from .stat_handler import HasStats
from .situational_effect import HasSituationalEffects, SituationalEffectHandler


class StatTestHandler(BaseHandler):

    # @BaseHandler.task_signature
    # def on_stat_test(stat_test: StatTest, tester: HasStats) -> Quality:
    #     ...

    def relative_difficulty(self, tester: HasStats, stat_test: StatTest = None, ) -> Difficulty:
        base_difficulty = StatTest.difficulty
        domain_competence = tester.competence_in(stat_test.domain)
        situational_effects = SituationalEffectHandler.get_effects_between(tester, stat_test)
        relative_difficulty_score = ( base_difficulty - domain_competence - situational_effects ) / 3
        return Difficulty(relative_difficulty_score)

    @staticmethod
    def default_resolution(stat_test: StatTest, tester: HasStats,
                           stat_domain: StatDomain = None,
                           tags: Tags = None,
                           **kwargs) -> Quality:
        relative_difficulty = StatTest.relative_difficulty(
            stat_test, tester, stat_domain=stat_domain, tags=tags)
        outcome = StatTest.test_outcome(relative_difficulty, **kwargs)
        return outcome
    BaseHandler.register_strategy(default_resolution, 'on_stat_test', priority=Priority.LAST)

    @classmethod
    def resolve_stat_test(cls, tester: HasStats,
                          difficulty: Difficulty = Difficulty.NORMAL,
                          **kwargs) -> Quality:

        result = cls.execute_task(tester, "on_stat_test", difficulty=difficulty, **kwargs, result_mode="first")
        return result


class StatTest(HasSituationalEffects, Entity):
    # Entity for has tags and situational effects

    difficulty: Difficulty = Field(default=Difficulty.NORMAL)
    domain: StatDomain = None
