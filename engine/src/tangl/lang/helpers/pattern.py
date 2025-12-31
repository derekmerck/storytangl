# pragma: exclude file - dependencies are optional and results are heavily cached
from __future__ import annotations
from typing import Literal

from tangl.utils.shelved2 import shelved

# The setup for this is fairly computationally intensive, so pattern is
# imported inside the caching wrapper.  If terms are all in cache, the
# runtime won't try to invoke pattern at all...

from tangl.lang.pronoun import PoV

try:  # pragma: no cover - exercised in integration tests
    from pattern.text.en import conjugate as _pattern_conjugate
    from pattern.text.en import pluralize as _pattern_pluralize
    from pattern.text.en import singularize as _pattern_singularize
except ImportError:  # pragma: no cover - dependency optional in CI
    _pattern_conjugate = None
    _pattern_pluralize = None
    _pattern_singularize = None


def _preserve_case(source: str, target: str) -> str:
    if not source:
        return target
    if source.isupper():
        return target.upper()
    if source[0].isupper():
        return target.capitalize()
    return target


def _fallback_progressive(verb: str) -> str:
    verb_lower = verb.lower()
    if verb_lower in {'be'}:
        return _preserve_case(verb, 'being')
    if verb_lower.endswith('ie'):
        return _preserve_case(verb, verb_lower[:-2] + 'ying')
    if verb_lower.endswith('e') and not verb_lower.endswith('ee'):
        return _preserve_case(verb, verb_lower[:-1] + 'ing')
    if verb_lower.endswith('run'):
        # double n (run -> running)
        return _preserve_case(verb, verb_lower + verb_lower[-1] + 'ing')
    return _preserve_case(verb, verb_lower + 'ing')


def _fallback_past(verb: str) -> str:
    verb_lower = verb.lower()
    irregular = {
        'be': 'was',
        'run': 'ran',
    }
    if verb_lower in irregular:
        return _preserve_case(verb, irregular[verb_lower])
    if verb_lower.endswith('e'):
        return _preserve_case(verb, verb_lower + 'd')
    if verb_lower.endswith('y') and verb_lower[-2:] not in {'ay', 'ey', 'iy', 'oy', 'uy'}:
        return _preserve_case(verb, verb_lower[:-1] + 'ied')
    return _preserve_case(verb, verb_lower + 'ed')


def _fallback_present_3s(verb: str) -> str:
    verb_lower = verb.lower()
    irregular = {
        'be': 'is',
        'run': 'runs',
    }
    if verb_lower in irregular:
        return _preserve_case(verb, irregular[verb_lower])
    if verb_lower.endswith(('s', 'sh', 'ch', 'x', 'z', 'o')):
        return _preserve_case(verb, verb_lower + 'es')
    if verb_lower.endswith('y') and verb_lower[-2:] not in {'ay', 'ey', 'iy', 'oy', 'uy'}:
        return _preserve_case(verb, verb_lower[:-1] + 'ies')
    return _preserve_case(verb, verb_lower + 's')


def _fallback_conjugate(verb: str, tense: str, person: int | None, number: str, aspect: str) -> str:
    verb_lower = verb.lower()

    if aspect == 'progressive':
        return _fallback_progressive(verb)

    if verb_lower == 'be':
        if tense == 'past':
            if number == 'plural' or person == 2:
                return _preserve_case(verb, 'were')
            return _preserve_case(verb, 'was')
        if tense in {'infinitive', 'present'}:
            if number == 'plural':
                return _preserve_case(verb, 'are')
            if person == 1:
                return _preserve_case(verb, 'am')
            if person == 2:
                return _preserve_case(verb, 'are')
            if person == 3:
                return _preserve_case(verb, 'is')
            return _preserve_case(verb, 'be')

    if tense == 'past':
        return _fallback_past(verb)

    if tense in {'infinitive', 'present'}:
        if person == 3 and number == 'singular':
            return _fallback_present_3s(verb)
        return verb

    return verb


def _fallback_is_plural(noun: str) -> bool:
    noun_lower = noun.lower()
    irregular_true = {'data', 'children', 'people'}
    irregular_false = {'datum', 'child', 'person'}
    if noun_lower in irregular_true:
        return True
    if noun_lower in irregular_false:
        return False
    if noun_lower.endswith(('ss', 'us')):
        return False
    if noun_lower.endswith('ves'):
        return True
    if noun_lower.endswith('ies'):
        return True
    if noun_lower.endswith('s') and not noun_lower.endswith('ss'):
        return True
    return False

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
    if _pattern_conjugate:
        return _pattern_conjugate(
            verb,
            tense=tense,
            person=person,
            number=number,
            aspect=aspect,
        )
    return _fallback_conjugate(verb, tense, person, number, aspect)

def is_plural(noun):
    if noun.endswith('ss'):
        # pattern doesn't do well with 'boss/bosses' or 'dress/dresses'
        return False
    return _is_plural(noun)

@shelved('plurals')
def _is_plural(noun):
    if _pattern_pluralize and _pattern_singularize:
        return _pattern_singularize(_pattern_pluralize(noun)) == noun
    return _fallback_is_plural(noun)
