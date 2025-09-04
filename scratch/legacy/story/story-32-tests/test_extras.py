import pytest

from tangl.story.concept import Actor, Extras
# from tangl.story.actor.enums import HairColor


def test_extras1():

    call = Extras(
        label='extras',
        actor_template={
        'name': "Extra Actor",  # todo: need to setup name sampler
        'look': { "hair_color": "green" }
    })
    extras = call.cast(n = 2)
    print( extras )

    assert len( extras ) == 2
    assert all( x.look.hair_color is HairColor.GREEN for x in extras )


def test_extras2():
    # Create an Extras instance
    extras = Extras(label="abc", actor_template={'label': 'dummy', 'name': 'John Dummy'})

    # Test initial role state
    assert extras.label == "ex-abc"
    assert extras.actor is None

    a = extras.cast(1)
    print( a )
    assert isinstance(a[0], Actor)
    assert a[0].label.startswith('dummy')
    print( a[0].label )

@pytest.mark.xfail(reason="reduce not working")
def test_extras_reduce_defaults():

    call = Extras(
        label='extras',
        actor_template={
        'name': "Extra Actor",  # todo: need to setup name sampler
        'look': {
            "hair_color": ["green", "red" ]
        }
    })
    extras = call.cast(n = 2)
    print( extras )

    assert len( extras ) == 2
    assert all( x.look.hair_color in [ HairColor.GREEN, HairColor.RED ] for x in extras )

