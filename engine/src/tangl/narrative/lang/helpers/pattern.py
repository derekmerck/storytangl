from typing import Literal

from tangl.utils.shelved2 import shelved

# The setup for this is fairly computationally intensive, so pattern is
# imported inside the caching wrapper.  If terms are all in cache, the
# runtime won't try to invoke pattern at all...

from tangl.narrative.lang.pronoun import PoV

def conjugate(verb, pov: PoV = PoV._3s, tense: str = "present", aspect: str = "imperfective"):
    """Wrapper for defaults"""

    person, plural = pov.person_and_plural()
    if plural:
        number = "plural"
    else:
        number = "singular"

    return _conjugate(verb, tense, person, number, aspect)


PATTERN_TENSE = Literal["infinitive", "present", "past", "future"]
PATTERN_PERSON = Literal[1, 2, 3, None]
PATTERN_NUM = Literal["SG", "PL"]
PATTERN_MOOD = Literal["indicative", "imperative", "conditional", "subjunctive"]
PATTERN_ASPECT = Literal["imperfective", "perfective", "progressive"]

@shelved('conjugate')
def _conjugate(verb,
              tense: PATTERN_TENSE,
              person: PATTERN_PERSON,
              number: PATTERN_NUM,
              aspect: PATTERN_ASPECT):
    from pattern.text.en import conjugate as conjugate_
    return conjugate_(
        verb,
        tense = tense,               # INFINITIVE, PRESENT, PAST, FUTURE
        person = person,             # 1, 2, 3 or None
        number = number,             # SG, PL
        # mood = "indicative",       # INDICATIVE, IMPERATIVE, CONDITIONAL, SUBJUNCTIVE
        aspect = aspect,             # IMPERFECTIVE, PERFECTIVE, PROGRESSIVE
        # negated = False            # True or False
    )

def is_plural(noun):
    if noun.endswith('ss'):
        # pattern doesn't do well with 'boss/bosses' or 'dress/dresses'
        return False
    return _is_plural(noun)

@shelved('plurals')
def _is_plural(noun):
    from pattern.text.en import pluralize, singularize
    return singularize(pluralize(noun)) == noun
    # return pluralize(singularize(noun)) == noun
