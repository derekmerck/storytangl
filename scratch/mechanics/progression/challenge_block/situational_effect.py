"""

trigger and effect

can be assigned through tags:
@domain.easier
@tag.harder
@tag.allow_x

need to provide a "donates_tags" field for tags that will be passed on to the bearer for badges/assets

@domain or @stat or @tag, if x.domain is or x.has(tag)
much_easier, easier, harder, much_harder

"""
from typing import Literal

from pydantic import BaseModel

from tangl.core import Entity
from .stat_handler import StatDomain

SituationalEffectHandler = object

EffectType = Literal['bonus', 'malus', 'cost', 'outcome', 'lock', 'unlock']

# these are probably singletons, too?
class SituationalEffect(BaseModel):
    applies_to: StatDomain = None
    effect_type: EffectType = None

class HasSituationalEffects(Entity):
    effects: list[SituationalEffect] = None

