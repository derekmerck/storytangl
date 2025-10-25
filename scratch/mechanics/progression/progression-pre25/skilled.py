import attr

from tangl.story.asset.badge import Badge
from .character import Character, SecondaryTrait
from .quality import QualityTier as Q

def SkilledCharacter(skills: dict = None, name: str = None, bases: tuple = None) -> type:

    attrs = {}
    for k, v in skills.items():

        if "minor_effects" in v:
            Badge(uid=f'{k}_minor', effects=v['minor_effects'], conditions=[f'{k} very low'])
            del v['minor_effects']
        if "effects" in v:
            Badge(uid=k, effects=v['effects'], conditions=[f'{k} ok'], hides=[f'{k}_minor'])
            del v['effects']
        if "major_effects" in v:
            Badge(uid=f'{k}_major', effects=v['master_effects'],
                  conditions=[f'{k} very good'], hides=[f'{k}_minor', k])
            del v['major_effects']

        # add governor on init
        attrs[k] = attr.ib(default=Q.MID,
                           type=SecondaryTrait,
                           converter=lambda x: SecondaryTrait(x, governors=v.get('governors')))

    if not bases:
        bases = (Character,)

    if not name:
        name = f"Skilled{bases[0].__name__}"

    res = attr.make_class(name, attrs, bases=bases)
    return res
