import pytest

from tangl.narrative.lang.conjugates import Conjugates
from tangl.narrative.lang.pronoun import PoV
from tangl.narrative.lang.helpers.pattern import is_plural, conjugate

conjugation_tests = {
    "runs": ("run", PoV._3s),
    "is": ("be", PoV._3s),
    "jump": ("jump", PoV._1s)
}

@pytest.mark.parametrize('expected, params', conjugation_tests.items())
def test_conjugation(expected, params):

    conj = conjugate(*params)
    print( f"conjugated {params} is {conj}" )
    assert conj == expected

def test_participle_conjugation():

    verb, past, gerund = "run", "ran", "running"
    conj = conjugate(verb, tense="past", aspect="imperfective")
    print( f"conjugated {verb} is {conj}" )
    assert conj == past

    conj = conjugate(verb, tense="present", aspect="progressive")
    print( f"conjugated {verb} is {conj}" )
    assert conj == gerund

def test_conjugates_from_pattern():

    to_be = Conjugates.from_pattern("be")
    print( to_be )

    assert to_be.conjugate(pov="inf") == "be"
    assert to_be.conjugate(pov=PoV._1s) == "am"
    assert to_be.conjugate(pov=PoV._3p) == "are"

    assert to_be.deconjugate("am") == PoV._1s
    assert to_be.deconjugate("be") == "infinitive"

def test_pattern_plurals():

    assert is_plural('dogs')
    assert not is_plural('dog')

    assert is_plural('dresses')
    assert not is_plural('dress')

    assert is_plural('scarves')
    assert not is_plural('scarf')

    assert is_plural('data')
    assert not is_plural('datum')

    assert is_plural('bosses')
    assert not is_plural('boss')

