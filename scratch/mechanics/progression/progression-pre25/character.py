from typing import *

import attr

from tangl.story import Actor
from scratch.quality.quality import Quality, QualityTier as Q, clamp

PrimaryTrait = Stat

class SecondaryTrait(Stat):
    # governor increases with gain, decreases with loss
    governors: list[Trait] = None

    # if a skill or secondary is lower than gov, it will grow
    def gain(self, quality: Q = Q.MID):
        self.incr(quality)
        for g in self.governors:
            g.incr(Q.VERY_LOW)

    # if a skill or secondary is higher than gov, it will decay
    def lose(self, quality: Q):
        self.decr(quality)
        for g in self.governors:
            g.decr(Q.VERY_LOW)


class StatCurrency(Stat):
    # governor increases with spend/exercise, decreases with restore
    governors: list[SecondaryTrait] = None

    # high gov makes costs cheaper
    def spend(self, quality: Q):
        self.decr(quality)
        for g in self.governors:
            g.incr(Q.VERY_LOW)
            self.val = clamp(self.val, 0, g.val)

    # high gov makes restores better
    def restore(self, quality: Q):
        self.incr(quality)
        for g in self.governors:
            g.decr(Q.VERY_LOW)
            self.val = clamp(self.val, 0, g.val)


class Character:
    """
    Opinionated character class.

    There are 5 trait "intrinsics" that determine the overall flavor
    of the character: body, spirit, mind, lewd, wealth.

    Intrinsics move very slowly as the result of secondary traits being
    exercised.

    The max and change rates for secondary traits are governed by intrinsic
    domains.  High intrinsics impart high maxes, but slower growth and decay.
    Lower intrinsics impart lower maxes, but faster growth and decay.

    Intrinsics and secondary traits default to mid/ok by definition.

    Skills are secondary traits that default to None and can be _trained_ through
    activities.

    Secondary traits commonly have three levels of badges at very low, ok, and
    very high.

    'Very low' indicates severe injury for a trait, or can unlock tagged activities
    like crafting for a skill.  'Very high' may provide a bonus for tagged activities.

    Currencies are fungible qualities that can be "spent" on activities and
    "restored" through rest.

    Activities may have many impacts.  'Training' activities can convert
    currencies to secondary trait or skill gains.
    """

    # Intrinsic traits, hard to move
    # ------------------------------
    body: Trait = None
    mind: Trait = None
    spirit: Trait = None
    lewd: Trait = None
    wealth: Trait = None

    # Secondary traits, mutable through actions
    # ------------------------------
    health: SecondaryTrait = None      # governed by body
    wit: SecondaryTrait = None         # governed by mind
    temper: SecondaryTrait = None      # governed by spirit
    corruption: SecondaryTrait = None  # governed by lewd
    influence: SecondaryTrait = None   # governed by wealth

    # Currencies, spendable or restored by actions
    # --------------------------------
    fatigue: TraitCurrency = None   # activities, fight, governed by health and temper
    will: TraitCurrency = None      # train, magic,      governed by wit and temper
    heat: TraitCurrency = None      # intimate,          governed by corruption and temper
    leverage: TraitCurrency = None  # goods/services,    governed by influence and temper

    # cash and prestige are aliases for leverage
    prestige = leverage  # particularly for chattel, negotiations
    cash = leverage      # for budgets, bookkeeping

    # Skills, mutable traits
    # These are similar to badges, they are added programmatically from spec


class Relationship:

    # Enable reward/punishment

    fear: SecondaryTrait = None  # governed by spirit
    # Double-ended trait
    # { TERRIFIED, FEARFUL, AMBIVALENT, TRUSTING, FAITHFUL }
    # loving: gain fear/lose trust = spirit down, gain trust/lose fear = spirit up
    # hateful: gain fear/lose trust = spirit up, gain trust/lose fear = spirit down
    @property
    def trust(self) -> SecondaryTrait:
        return 1.0 - self.fear
    @trust.setter
    def trust(self, value: SecondaryTrait):
        self.fear = 1.0 - value

    hate: SecondaryTrait = None  # governed by spirit
    # { HATEFUL, SOUR, NEUTRAL, AMIABLE, LOVING }
    # trusting: gain hate/lose love = spirit down, gain love/lose hate = spirit up
    # fearful: gain hate/lose love = spirit up, gain love/lose hate = spirit down
    @property
    def love(self) -> SecondaryTrait:
        return 1.0 - self.hate
    @love.setter
    def love(self, value: SecondaryTrait):
        self.hate = 1.0 - value

    def reward(self, quality: Q):
        self.trust.gain(quality)
        # self.fear.lose(quality)
        self.love.gain(quality)
        # self.hate.lose(quality)

    def punish(self, quality: Q):
        self.fear.gain(quality)
        self.hate.gain(quality)
