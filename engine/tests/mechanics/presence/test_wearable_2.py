import pytest

pytest.skip(allow_module_level=True, reason="not refactored")

from scratch.mechanics.look.wearable import WearableType, Wearable, WearableState, WearableLayer
from tangl.lang.nominal import DeterminativeType as DT

@pytest.fixture()
def load_wearable_types():
    WearableType.clear_instances()
    WearableType.load_instances_from_yaml()


@pytest.fixture
def wearables():

    WearableType.clear_instances()

    # Creating instances of WearableType
    coat  = WearableType(label='coat',  covers={BodyRegion.UPPER})
    shirt = WearableType(label='shirt', covers={BodyRegion.UPPER}, layer=WearableLayer.OVER, noun='shirt')
    pants = WearableType(label='pants', covers={BodyRegion.LOWER}, layer=WearableLayer.OVER, noun='pants')
    socks = WearableType(label='socks', covers={BodyRegion.FEET}, layer=WearableLayer.INNER)
    shoes = WearableType(label='shoes', covers={BodyRegion.FEET}, noun='shoes')
    dress = WearableType(label='dress', covers={BodyRegion.LOWER, BodyRegion.UPPER}, noun='dress')
    exclusive_dress = WearableType(label='exclusive_dress', from_ref='dress', tags={'exclusive'})

    yield Wearable(coat), Wearable(shirt), Wearable(pants), Wearable(socks), Wearable(shoes), Wearable(dress), Wearable(exclusive_dress)

    # teardown - restore wearables to original state
    WearableType.clear_instances()
    WearableType.load_instances_from_yaml()


def test_wearable_singleton_unique(load_wearable_types):

    shirt_type = WearableType.get_instance('shirt')
    print( shirt_type )
    assert shirt_type.noun == "shirt"
    assert shirt_type.plural is False

    shirt_type2 = WearableType(label="shirt")
    assert shirt_type2 is shirt_type


def test_wearable_type(load_wearable_types):
    # print( WearableType._instances )

    coat_type = WearableType.get_instance('coat')
    print( coat_type )
    coat_inst = Wearable('coat')
    print( coat_inst )

    shirt_type = WearableType.get_instance('shirt')
    print( shirt_type )

    assert shirt_type.layer < coat_type.layer


def test_wearable_from_ref(wearables):

    dress, exclusive_dress = wearables[-2:]

    print( dress.reference_entity )
    print( exclusive_dress.reference_entity )

    assert exclusive_dress.has_tags("exclusive")
    assert exclusive_dress.noun == "dress"

    green_pants = Wearable(label="green_pants",
                           color="green",
                           from_ref="pants")
    assert green_pants.color == "green"
    assert green_pants.noun == "pants"


def test_print_default_wearables(load_wearable_types):
    res = []
    for v in WearableType._instances.values():
        res.append( v.model_dump(exclude_none=True, exclude_defaults=True, exclude_unset=True) )
    from pprint import pprint
    pprint( res )


def test_print_default_wearables2(load_wearable_types):
    # clear it and try again
    res = []
    for v in WearableType._instances.values():
        res.append( v.model_dump(exclude_none=True, exclude_defaults=True, exclude_unset=True) )
    from pprint import pprint
    pprint( res )

def test_wearable_instances(wearables):
    coat, shirt, pants, socks, shoes, dress, exclusive_dress = wearables

    print( coat )
    print( coat.reference_entity )
    print( coat.__class__.mro() )
    assert coat.label == 'coat'
    assert shirt.layer == WearableLayer.OVER
    assert pants.noun == 'pants'
    print( exclusive_dress.tags )
    assert exclusive_dress.is_exclusive()  # can't be a property b/c its a singleton method


def test_wearable_covers_multiple_regions(wearables):
    dress = wearables[-2]
    assert BodyRegion.UPPER in dress.covers
    assert BodyRegion.LOWER in dress.covers


def test_state_transition(wearables):
    coat, _, _, _, _, _, _ = wearables

    # Valid transition
    assert coat.state is WearableState.ON
    assert WearableHandler.can_transition(coat, WearableState.OFF)
    assert coat.can_transition(WearableState.OFF)
    coat.transition(WearableState.OFF)
    assert coat.state is WearableState.OFF

    # Invalid transition (e.g., from OFF to OPEN is not applicable)
    assert not coat.can_transition(WearableState.OPEN)
    with pytest.raises(ValueError):
        coat.transition(WearableState.OPEN)


def test_serialization_and_deserialization(wearables):
    coat, _, _, _, _, _, _ = wearables

    # Serialize and then deserialize the coat
    serialized_coat = GraphStructuringHandler().unstructure(coat)
    deserialized_coat = GraphStructuringHandler().structure(serialized_coat)

    # Check if the deserialized object maintains the same properties
    assert deserialized_coat.label is coat.label
    assert deserialized_coat.state is coat.state


def test_wearable_plural_default():

    jorts = WearableType(label="jorts")
    assert jorts.plural is True

    glove = WearableType(label="glove")
    assert glove.plural is False


## Setup for tests
@pytest.fixture
def alt_wearables():
    tshirt = Wearable(label='shirt',
                      nouns=["tshirt"],
                      layer=WearableLayer.INNER,
                      adjectives=['soft'],
                      covers={BodyRegion.TOP})
    jeans = Wearable(label='pants',
                     nouns=["jeans"],
                     color="blue",
                     plural=True,
                     quantifiers=['pair of'],
                     adjectives=['worn'],
                     layer=WearableLayer.OUTER, covers={BodyRegion.BOTTOM})
    jacket = Wearable(label='coat',
                      nouns=["jacket"],
                      color=['dark'],
                      adjectives=['fancy'],
                      layer=WearableLayer.OUTER,
                      covers={BodyRegion.TOP})

    yield tshirt, jeans, jacket

@pytest.mark.xfail(reason="old code?")
def test_wearable_renders(alt_wearables):
    tshirt, jeans, jacket = alt_wearables
    print( tshirt.render_desc() )
    assert tshirt.render_desc() == "a soft tshirt"
    print( tshirt.render_desc(dt=DT.DDET) )
    assert tshirt.render_desc(dt=DT.DDET) == "the soft tshirt"



# Test cases for Outfit methods
