import itertools
import operator

from tangl.lang.pronoun import Pronoun, Gens, PoV, PT

import pytest

params = list( itertools.product(PoV.__members__.values(), Gens.__members__.values()) )
@pytest.mark.parametrize( ('p', 'g'), params )
def test_pronouns( p, g ):
    print("I", Pronoun.subjective(p, g))
    print("me", Pronoun.objective(p, g))
    print("myself", Pronoun.objective(p, g, reflexive=True))
    print("mine", Pronoun.possessive(p, g))
    print("my", Pronoun.possessive(p, g, adjective=True))

    if p == PoV._1s:
        assert operator.eq("I", Pronoun.subjective(p, g))
        assert operator.eq("me", Pronoun.objective(p, g))
        assert operator.eq("myself", Pronoun.objective(p, g, reflexive=True))
        assert operator.eq("mine", Pronoun.possessive(p, g))
        assert operator.eq("my", Pronoun.possessive(p, g, adjective=True))


def test_subjective_pronouns():
    test_cases = [
        (PoV._1s, Gens.XY, "I"),
        (PoV._1s, Gens.XX, "I"),
        (PoV._1s, Gens.X_, "I"),
    ]
    for pov, gens, expected in test_cases:
        result = Pronoun.subjective(pov, gens)
        assert result == expected

def test_possessive_pronouns():
    test_cases = [
        (PoV._1s, Gens.XY, False, "mine"),
        (PoV._1s, Gens.XY, True, "my"),
    ]
    for pov, gens, adj, expected in test_cases:
        result = Pronoun.possessive(pov, gens, adjective=adj)
        assert result == expected

def test_objective_pronouns():
    test_cases = [
        (PoV._1s, Gens.XY, False, "me"),
        (PoV._1s, Gens.XY, True, "myself"),
    ]
    for pov, gens, reflex, expected in test_cases:
        result = Pronoun.objective(pov, gens, reflexive=reflex)
        assert result == expected

def test_pov_of():
    assert Pronoun.pov_of("I") == PoV._1s
    assert Pronoun.pov_of("you") == PoV._2s
    assert Pronoun.pov_of("they") == PoV._3p

def test_gender_of():
    assert Pronoun.gender_of("he") == Gens.XY
    assert Pronoun.gender_of("she") == Gens.XX
    assert Pronoun.gender_of("it") == Gens.X_

def test_type_of():
    assert Pronoun.type_of("I") == PT.S
    assert Pronoun.type_of("me") == PT.O
    assert Pronoun.type_of("mine") == PT.P

def test_pnp():
    pnp = PoV.person_and_plural
    assert pnp( PoV._1s ) == (1, False)
    assert pnp( PoV._2p ) == (2, True)

@pytest.mark.parametrize('pov', PoV.__members__.values())
def test_pnp_casting(pov):
    pnp = PoV.person_and_plural
    res = pnp( pov )
    assert PoV(res) == pov

@pytest.mark.parametrize('data', [('I',"_1s"), ('your', "_2s" ), ('themselves', "_3p")])
def test_pov_of(data):
    s, e = data
    print( s, e )
    assert Pronoun.pov_of(s) == PoV(e)


def test_pl():
    assert PoV._1s.plural() is PoV._1p


def test_jinja_pronoun_filters():

    from types import SimpleNamespace as Box
    import jinja2

    env = jinja2.Environment()
    Pronoun.register_pronoun_filters(env)

    s = "{{ a | she }} has {{ a | her_ }} dog with {{ a | her }}"
    t = env.from_string(s)

    a = Box(**{'is_xx': True})
    s = t.render(a=a)
    print(s)
    assert s == "she has her dog with her"

    a = Box(**{'is_xx': False})
    s = t.render(a=a)
    print(s)
    assert s == "he has his dog with him"

    s = "{{ a | She }} has {{ a | Her_ }} dog with {{ a | Her }}"

    t = env.from_string(s)

    a = Box(**{'is_xx': True})
    s = t.render(a=a)
    print(s)
    assert s == "She has Her dog with Her"

    a = Box(**{'is_xx': False})
    s = t.render(a=a)
    print(s)
    assert s == "He has His dog with Him"





