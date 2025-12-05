import yaml
import attr

from tangl.world.narrator.rejinja.word import Word, Phrase
from tangl.world.narrator.rejinja import EnumReferent as Referent

fat = Word(
    uid="fat",
    **{ "thin": ["thin"],
        "fat":  ["fat"] }
)

def test_idempotent():
    assert Word(fat) == fat


@attr.define
class Example( Referent ):

    weight: int = 100

    class Qualifier(Referent.Qualifier):
        THIN = "thin", lambda self: self.weight < 25
        FAT = "fat", lambda self: self.weight > 75


def test_word_qualification():

    obj1 = Example( weight=10 )
    assert( obj1.qualified_by( "thin" ) )
    assert( not obj1.qualified_by( "fat" ) )
    assert( fat(obj1) in ["thin", "moderate"] )

    obj2 = Example( weight=90 )
    assert( not obj2.qualified_by( Example.Qualifier.THIN ) )
    assert( obj2.qualified_by( Example.Qualifier.FAT ) )
    assert( fat(obj2) in ["fat", "moderate"] )


thing = Word(
    uid='thing',
    **{ "thin": ["stick"],
        "fat":  ["blob"] }
)

phrase = Phrase(
    uid = "phrase",
    words = {'adj': fat,
             'noun': thing}
)

def test_phrase():

    obj1 = Example( weight=10 )
    obj2 = Example( weight=90 )

    assert( phrase(obj1) == "thin stick" )
    assert( phrase(obj2) == "fat blob" )

# language=YAML
spec_ = """
---
phrase:
  words:
    adj:
      thin:
        - thin
      fat:
        - fat
    noun:
      thin:
        - stick
      fat:
        - blob
"""

def test_loader():

    spec = yaml.safe_load(spec_)
    phrase_ = Phrase( uid="phrase", **spec['phrase'] )

    assert phrase_ == phrase
    print( phrase_ )

    obj1 = Example( weight=10 )
    obj2 = Example( weight=90 )

    print( phrase_(obj1) )
    print( phrase_(obj2) )

    assert phrase_(obj1) == phrase(obj1)
    assert phrase_(obj2) == phrase(obj2)


def test_multiple():
    with open('sample_lingo.yaml') as f:
        spec = yaml.safe_load(f)

    @attr.define
    class Obj(Referent):

        price: int = 50

        class Qualifier(Referent.Qualifier):
            FANCY = 'fancy', lambda self: self.price > 75
            CHEAP = 'cheap', lambda self: self.price < 25

    cheap_thing = Obj(price=10)
    fancy_thing = Obj(price=90)

    for uid, word in spec['words'].items():
        w = Word(uid=uid, **word)
        print(w(cheap_thing))
        print(w(fancy_thing))

    for uid, phrase in spec['phrases'].items():
        p = Phrase(uid=uid, **phrase)
        print(p(cheap_thing))
        print(p(fancy_thing))

    print(Phrase._instances.keys())
    print(Phrase._instances['fancy_pen'])

    p = Phrase["fancy_pen"]
    print(p)
    print(p(cheap_thing))
    print(p(fancy_thing))

# def test_pronouns():
#
#     s = "He says hello"
#
#     env = JingoEnvironment(preprocessors=[expand_pronouns,reconjugate_verbs])
#     t = env.from_string(s)
#     print( t.source )
#
#     ss = t.render(Him=types.SimpleNamespace(**{'gens':'xx','pov':1}))
#     print( ss )
#     assert( ss == "I say hello")
#
#     ss = t.render(Him=types.SimpleNamespace(**{'gens':'x_','pov':3}))
#     print( ss )
#     assert( ss == "It says hello")
